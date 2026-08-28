import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.sanitize import sanitize_user_id
from app.utils import clean_uuid
from app.services.billing_service import (
    get_user_subscription,
    create_checkout_session,
    handle_stripe_webhook
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])

class BillingStatusResponse(BaseModel):
    user_id: str
    tier: str
    status: str
    expires_at: Optional[str] = None

class BillingCheckoutRequest(BaseModel):
    user_id: str
    tier: str
    success_url: str
    cancel_url: str

class BillingCheckoutResponse(BaseModel):
    checkout_url: str

@router.get("/api/billing/status", response_model=BillingStatusResponse)
@limiter.limit("10/minute")
async def get_billing_status(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve subscription details for a specific user ID."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view billing status for this user"
        )
    user_id = sanitized_id
    sub = get_user_subscription(user_id)
    exp_str = sub["expires_at"].isoformat() if sub.get("expires_at") else None
    return BillingStatusResponse(
        user_id=user_id,
        tier=sub["tier"],
        status=sub["status"],
        expires_at=exp_str
    )

@router.post("/api/billing/checkout", response_model=BillingCheckoutResponse)
@limiter.limit("10/minute")
async def create_billing_checkout(request: Request, payload: BillingCheckoutRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Generate checkout session URL for upgrading subscription tier."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to checkout for this user"
        )
    payload.user_id = sanitized_id
    try:
        url = create_checkout_session(
            payload.user_id, payload.tier, payload.success_url, payload.cancel_url
        )
        return BillingCheckoutResponse(checkout_url=url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    """Receive Stripe transaction webhooks to coordinate subscription updates."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    success = handle_stripe_webhook(payload, sig_header)
    if not success:
        raise HTTPException(status_code=400, detail="Webhook signature check failed")
    
    return {"status": "success"}

@router.post("/api/billing/mock-confirm")
async def mock_confirm_billing(payload: BillingCheckoutRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Simulates webhook activation of subscription when stripe is in dev mock mode."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id or clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.services.billing_service import update_user_subscription
    import datetime
    future_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    update_user_subscription(sanitized_id, payload.tier, "active", "mock_customer_id", "mock_sub_id", future_exp)
    return {"status": "success", "message": f"Successfully simulated checkout webhook for {sanitized_id} -> {payload.tier}"}
