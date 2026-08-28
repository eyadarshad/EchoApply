import logging
import datetime
from typing import Dict, Any, Optional
import psycopg
from app.config import settings
from app.utils import clean_uuid

logger = logging.getLogger(__name__)

if settings.STRIPE_SECRET_KEY:
    stripe_api_key = settings.STRIPE_SECRET_KEY
    try:
        import stripe
        stripe.api_key = stripe_api_key
    except ImportError:
        logger.warning("stripe package not installed.")
else:
    try:
        import stripe
    except ImportError:
        pass

def _connect():
    """Create a short-lived DB connection with a 1-second timeout."""
    return psycopg.connect(settings.DATABASE_URL, connect_timeout=1)

def get_user_subscription(user_id: str) -> Dict[str, Any]:
    """Fetch current subscription status for a user, returning a default 'free' plan if not found."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tier, status, expires_at 
                    FROM subscriptions 
                    WHERE user_id = %s;
                    """,
                    (clean_uuid(user_id),)
                )
                row = cur.fetchone()
                if row:
                    tier, status, expires_at = row
                    # Check for expiration
                    if expires_at and expires_at < datetime.datetime.now(datetime.timezone.utc):
                        return {"tier": "free", "status": "expired", "expires_at": expires_at}
                    return {"tier": tier, "status": status, "expires_at": expires_at}
    except Exception as e:
        logger.warning(f"Database subscription lookup failed: {e}")
        
    return {"tier": "free", "status": "active", "expires_at": None}

def update_user_subscription(
    user_id: str, 
    tier: str, 
    status: str, 
    customer_id: Optional[str] = None, 
    subscription_id: Optional[str] = None, 
    expires_at: Optional[datetime.datetime] = None
) -> bool:
    """Insert or update user subscription in DB."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO subscriptions (user_id, tier, status, stripe_customer_id, stripe_subscription_id, expires_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE 
                    SET tier = EXCLUDED.tier,
                        status = EXCLUDED.status,
                        stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, subscriptions.stripe_customer_id),
                        stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, subscriptions.stripe_subscription_id),
                        expires_at = COALESCE(EXCLUDED.expires_at, subscriptions.expires_at),
                        updated_at = NOW();
                    """,
                    (clean_uuid(user_id), tier, status, customer_id, subscription_id, expires_at)
                )
                conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update subscription in DB: {e}")
        return False

def create_checkout_session(user_id: str, tier: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe checkout session URL, or mock URL if keys are not set."""
    if not settings.STRIPE_SECRET_KEY:
        # Mock mode
        logger.info(f"Stripe keys not set. Simulating Pro checkout for user {user_id}.")
        return f"{success_url}?session_id=mock_stripe_session_id"

    # Stripe pricing catalog identifiers
    prices = {
        "pro": "price_pro_subscription_id_placeholder",
        "enterprise": "price_ent_subscription_id_placeholder",
    }
    price_id = prices.get(tier.lower())
    if not price_id:
        raise ValueError(f"Invalid tier selection: {tier}")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            client_reference_id=user_id,
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"tier": tier, "user_id": user_id}
        )
        return session.url
    except Exception as e:
        logger.error(f"Stripe Session creation error: {e}")
        raise ValueError(f"Stripe session creation failed: {e}")

def handle_stripe_webhook(payload: bytes, sig_header: str) -> bool:
    """Process Stripe webhooks to keep subscription states synchronized."""
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe credentials missing. Ignoring webhook.")
        return False

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Invalid webhook signature: {e}")
        return False

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        user_id = data_object.get("client_reference_id")
        sub_id = data_object.get("subscription")
        cust_id = data_object.get("customer")
        tier = data_object.get("metadata", {}).get("tier", "pro")
        
        # Calculate expiration
        future_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        update_user_subscription(user_id, tier, "active", cust_id, sub_id, future_exp)
        logger.info(f"Stripe upgrade succeeded for {user_id} -> {tier}")

    elif event_type in ["invoice.payment_succeeded", "invoice.payment_failed"]:
        sub_id = data_object.get("subscription")
        cust_id = data_object.get("customer")
        status = "active" if event_type == "invoice.payment_succeeded" else "incomplete"
        
        # Query user_id from sub_id or customer
        try:
            with _connect() as conn:
                user_id = None
                tier = "pro"
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id, tier FROM subscriptions WHERE stripe_subscription_id = %s;", (sub_id,))
                    row = cur.fetchone()
                    if row:
                        user_id, tier = row
                
                if user_id:
                    future_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                    update_user_subscription(user_id, tier, status, cust_id, sub_id, future_exp)
                    logger.info(f"Updated subscription invoice status for {user_id} -> {status}")
        except Exception as e:
            logger.error(f"Failed processing invoice webhook: {e}")

    elif event_type == "customer.subscription.deleted":
        sub_id = data_object.get("id")
        try:
            with _connect() as conn:
                user_id = None
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM subscriptions WHERE stripe_subscription_id = %s;", (sub_id,))
                    row = cur.fetchone()
                    if row:
                        user_id = row[0]
                
                if user_id:
                    # Revert to free tier
                    update_user_subscription(user_id, "free", "canceled", expires_at=datetime.datetime.now(datetime.timezone.utc))
                    logger.info(f"Canceled subscription for user {user_id}")
        except Exception as e:
            logger.error(f"Failed processing deletion webhook: {e}")

    return True

def record_usage(user_id: str, action_type: str, tokens_used: int = 0, cost_usd: float = 0.0, model: str = "") -> bool:
    """Inserts a resource usage record for the candidate."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usage_records (user_id, action_type, tokens_used, cost_usd, model)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (clean_uuid(user_id), action_type, tokens_used, cost_usd, model)
                )
                conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to record usage in DB: {e}")
        return False

def check_entitlement(user_id: str, action_type: str) -> bool:
    """
    Checks if user is entitled to perform action.
    Free tier limit checks:
    - 'tailor': limit 3 per day
    - 'llm_call': limit 20 per day
    - 'pdf_generation': limit 5 total
    - 'docx_generation': limit 5 total
    """
    sub = get_user_subscription(user_id)
    if sub.get("tier") in ["pro", "enterprise"]:
        return True
        
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                if action_type in ("pdf_generation", "docx_generation"):
                    cur.execute(
                        "SELECT COUNT(*) FROM usage_records WHERE user_id = %s AND action_type = %s;",
                        (clean_uuid(user_id), action_type)
                    )
                    count = cur.fetchone()[0]
                    if count >= 5:
                        return False
                elif action_type in ["tailor", "llm_call"]:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM usage_records 
                        WHERE user_id = %s 
                          AND action_type = %s 
                          AND created_at > NOW() - INTERVAL '1 day';
                        """,
                        (clean_uuid(user_id), action_type)
                    )
                    count = cur.fetchone()[0]
                    limit = 3 if action_type == "tailor" else 20
                    if count >= limit:
                        return False
        return True
    except Exception as e:
        # DENY on DB failure for free-tier users to prevent quota bypass during outages
        logger.warning(f"Error checking entitlement in DB (defaulting to DENY for safety): {e}")
        return False
