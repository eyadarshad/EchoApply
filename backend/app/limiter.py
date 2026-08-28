import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from app.config import settings

logger = logging.getLogger(__name__)

# Choose storage backend
storage_uri = settings.REDIS_URL
if storage_uri:
    logger.info("Initializing Limiter with Redis storage backend.")
else:
    logger.info("Initializing Limiter with in-memory storage backend.")
    storage_uri = "memory://"

# Tighten limits for production
default_limit = "120/minute" if settings.ENVIRONMENT == "production" else "200/minute"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=[default_limit]
)

def get_user_or_ip_key(request: Request) -> str:
    """
    Composite key function: tries to identify request by authenticated user_id,
    falling back to IP address if unauthenticated.
    """
    dev_user_id = request.headers.get("X-Dev-User-Id", "")
    if dev_user_id:
        return f"user:{dev_user_id}"
        
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            import base64
            import json
            parts = token.split(".")
            if len(parts) == 3:
                payload_b64 = parts[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
        except Exception:
            pass
            
    return get_remote_address(request)
