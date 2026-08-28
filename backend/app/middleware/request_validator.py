"""
Middleware for validating request payloads, content types, and injecting request IDs.
"""

import uuid
import logging
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class RequestValidatorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Inject X-Request-ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # 2. Enforce request size limit (10MB)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 10 * 1024 * 1024:  # 10MB
                    return JSONResponse(
                        status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                        content={"detail": "Request body too large. Maximum size allowed is 10MB."}
                    )
            except ValueError:
                pass
                
        # 3. Validate Content-Type for POST/PUT requests
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if content_length and int(content_length) > 0:
                if not any(t in content_type for t in ("application/json", "multipart/form-data", "application/x-www-form-urlencoded")):
                    return JSONResponse(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        content={"detail": f"Unsupported media type: {content_type}"}
                    )
                    
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
