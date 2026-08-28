import os
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, get_optional_user, AuthenticatedUser
from app.schemas import FrontendErrorLogRequest
from app.sanitize import sanitize_user_id, sanitize_text_input
from app.utils import clean_uuid
from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])

@router.delete("/api/user/delete")
@limiter.limit("5/minute")
async def gdpr_delete_user(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """GDPR Compliance: Completely wipes all user database records and local storage fallback files."""
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete this user"
        )
    user_id = sanitized_id
    user_uuid = clean_uuid(user_id)
    logger.info(f"GDPR: Initiating complete data deletion for user: {user_id}")
    
    try:
        fallback_dir = os.path.join(settings.DATA_DIR, "credentials")
        if os.path.exists(fallback_dir):
            for f in os.listdir(fallback_dir):
                if f.startswith(user_uuid):
                    os.remove(os.path.join(fallback_dir, f))
                    
        resumes_dir = os.path.join(settings.DATA_DIR, "resumes")
        if os.path.exists(resumes_dir):
            for f in os.listdir(resumes_dir):
                if f.startswith(user_uuid):
                    os.remove(os.path.join(resumes_dir, f))
    except Exception as cleanup_err:
        logger.warning(f"Failed to clean local storage files: {cleanup_err}")
        
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM users WHERE id = %s;", (user_uuid,))
                    await conn.commit()
                    return {"status": "success", "message": "All data and profile details wiped successfully."}
            raise HTTPException(status_code=500, detail="Database connection pool unavailable.")
    except Exception as e:
        logger.error(f"Failed to wipe user database records: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/errors/log")
@limiter.limit("30/minute")
async def log_frontend_error(request: Request, payload: FrontendErrorLogRequest, user: Optional[AuthenticatedUser] = Depends(get_optional_user)):
    """
    Log frontend client exceptions to the backend logger streams.
    Additionally routes to Sentry if initialized.
    """
    
    if payload.error_name:
        payload.error_name = sanitize_text_input(payload.error_name, max_length=200, field_name="error_name")
    if payload.error_message:
        payload.error_message = sanitize_text_input(payload.error_message, max_length=1000, field_name="error_message")
    if payload.stack_trace:
        payload.stack_trace = sanitize_text_input(payload.stack_trace, max_length=10000, field_name="stack_trace")
    if payload.url:
        payload.url = sanitize_text_input(payload.url, max_length=2000, field_name="url")
    if payload.user_id:
        sanitized_id = sanitize_user_id(payload.user_id)
        if sanitized_id:
            if user and clean_uuid(user.user_id) != clean_uuid(sanitized_id):
                logger.warning(f"[BOLA warning] Error log user mismatch. Auth: {user.user_id}, Payload: {payload.user_id}")
                payload.user_id = user.user_id
            else:
                payload.user_id = sanitized_id
        else:
            payload.user_id = None
    msg = (
        f"[Client-Side Error] Name: {payload.error_name} | Message: {payload.error_message}\n"
        f"URL: {payload.url or 'N/A'} | User: {payload.user_id or 'Anonymous'}\n"
        f"Stack Trace:\n{payload.stack_trace or 'No stack trace provided'}"
    )
    logger.error(msg)

    # Route explicitly to Sentry if settings.SENTRY_DSN is active
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            scope_manager = getattr(sentry_sdk, "isolation_scope", sentry_sdk.push_scope)
            with scope_manager() as scope:
                scope.set_tag("origin", "frontend")
                if payload.user_id:
                    if hasattr(scope, "set_user"):
                        scope.set_user({"id": payload.user_id})
                    else:
                        scope.user = {"id": payload.user_id}
                if payload.url:
                    scope.set_extra("url", payload.url)
                sentry_sdk.capture_message(
                    f"Frontend: {payload.error_name}: {payload.error_message}",
                    level="error"
                )
        except Exception as sentry_err:
            logger.error(f"Failed to forward error to Sentry: {sentry_err}")

    return {"status": "success", "message": "Frontend error logged successfully."}

class KillSwitchRequest(BaseModel):
    integration_name: str
    action: str  # "open" (disable) or "close" (enable)

@router.get("/api/admin/circuit-status")
async def get_circuit_status(user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve state of all registered circuit breakers."""
    if user.role != "admin":
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Admin only")
    
    from app.services.circuit_breaker import CIRCUIT_REGISTRY
    return {
        name: {
            "state": cb.state,
            "failure_count": cb.failure_count,
            "last_state_change": cb.last_state_change
        }
        for name, cb in CIRCUIT_REGISTRY.items()
    }

@router.post("/api/admin/kill-switch")
async def toggle_kill_switch(payload: KillSwitchRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Force override a circuit breaker state (manual kill switch)."""
    if user.role != "admin":
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Admin only")
            
    from app.services.circuit_breaker import get_circuit_breaker
    cb = get_circuit_breaker(payload.integration_name)
    if payload.action == "open":
        cb.state = "OPEN"
        cb.last_state_change = float('inf') # open indefinitely
        logger.warning(f"Admin triggered manual kill switch for {payload.integration_name}")
    else:
        cb.state = "CLOSED"
        cb.failure_count = 0
        cb.last_state_change = 0.0
        logger.info(f"Admin reset circuit breaker for {payload.integration_name}")
        
    return {"status": "success", "integration": payload.integration_name, "state": cb.state}

@router.get("/api/admin/metrics")
@limiter.limit("10/minute")
async def get_metrics(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve all logged telemetry and performance metrics."""
    if user.role != "admin":
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Admin only")
    from app.services.metrics import metrics_service
    return metrics_service.get_all()

