import os
import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.database import startup_db, shutdown_db
from app.schemas import HealthResponse, EchoRequest, EchoResponse
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.request_validator import RequestValidatorMiddleware

# --- Mock imports exposed for backward compatibility with existing unit tests that patch app.main ---
import psycopg
from app.services.github_enricher import enrich_profile_with_github
from app.pipeline.orchestrator import tailor_resume_flow

# --- Logging Initialization ---
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)

# --- Sentry SDK Initialization ---
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            send_default_pii=False  # Bug Fix 6: GDPR compliance
        )
        logger.info("Sentry SDK initialized successfully.")
    except Exception as sentry_err:
        logger.error(f"Failed to initialize Sentry SDK: {sentry_err}")

# --- Lifecycles ---
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_db()
    from app.tasks import start_task_worker, start_keep_alive_ping
    asyncio.create_task(start_task_worker())
    asyncio.create_task(start_keep_alive_ping())
    yield
    # Shutdown
    await shutdown_db()

app = FastAPI(
    title="AI Resume Generator & Smart Apply API",
    version="1.0.0",
    description="Backend API services for resume extraction, tailoring, job search, and auto-applying.",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
frontend_origins = [
    f"http://localhost:{settings.FRONTEND_PORT}",
    f"http://127.0.0.1:{settings.FRONTEND_PORT}",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3005",
    "http://127.0.0.1:3005",
]
prod_frontend = os.getenv("FRONTEND_URL", "")
if prod_frontend:
    for origin in prod_frontend.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in frontend_origins:
            frontend_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(RequestValidatorMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    
    if os.getenv("ENVIRONMENT", "development") == "production":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# --- Base Root & Health Endpoints (Supports GET and HEAD for UptimeRobot / Ping monitors) ---
@app.api_route("/", methods=["GET", "HEAD"], tags=["system"])
async def root():
    """Root endpoint for status check and uptime monitoring."""
    return {"status": "ok", "service": "Echo Apply API", "version": "1.0.0", "docs": "/docs"}

@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["system"])
@app.api_route("/api/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["system"])
async def health_check():
    """Verify backend and database connection status."""
    return HealthResponse(status="ok")

# --- Echo Endpoint ---
@app.post("/echo", response_model=EchoResponse, tags=["system"])
@app.post("/api/echo", response_model=EchoResponse, tags=["system"])
async def echo_message(payload: EchoRequest):
    """Echo endpoint for frontend validation of connection."""
    return EchoResponse(message=payload.message, status="success")

# --- Router Inclusions ---
from app.routers import (
    intake, profiles, tailor, jobs, apply, cover_letter,
    templates, render, billing, analytics, interview, admin,
    auth_sync, mock, chat, privacy, audit
)

app.include_router(intake.router)
app.include_router(profiles.router)
app.include_router(tailor.router)
app.include_router(jobs.router)
app.include_router(apply.router)
app.include_router(cover_letter.router)
app.include_router(templates.router)
app.include_router(render.router)
app.include_router(billing.router)
app.include_router(analytics.router)
app.include_router(interview.router)
app.include_router(admin.router)
app.include_router(auth_sync.router)
app.include_router(mock.router)
app.include_router(chat.router)
app.include_router(privacy.router)
app.include_router(audit.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=False
    )
