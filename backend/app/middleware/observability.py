import time
import uuid
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.services.metrics import metrics_service

logger = logging.getLogger("app.observability")

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Inject or reuse request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 2. Track timing
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log unhandled exceptions
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": round(duration_ms, 2),
                "error": str(exc)
            }
            logger.error(json.dumps(log_data))
            # Record the failed request in metrics
            metrics_service.record_request(request.url.path, 500, duration_ms)
            raise exc
            
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Inject Request ID header into response
        response.headers["X-Request-ID"] = request_id
        
        # 3. Log structured entry
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
        logger.info(json.dumps(log_data))

        # 4. Feed into metrics service
        metrics_service.record_request(request.url.path, response.status_code, duration_ms)
        
        return response
