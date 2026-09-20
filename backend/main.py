"""
Sentinel Backend - FastAPI Application Entry Point
Dual-mounted for Android Mobile APK (/api) and Admin Web Console (/api and /api/v1)
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine
from app.routers import (
    auth,
    users,
    personnel,
    alerts,
    risk,
    analytics,
    audit,
    journals,
    assessments,
    settings as settings_router,
    ai,
    voice,
    support,
    admin_console,
    hrms,
    biometrics,
    interventions,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sentinel Personnel Stress & Welfare Monitoring System API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Browser CORS is opt-in in production. Android and the desktop BFF are not
# browser cross-origin clients and do not require permissive CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response

# Router registry
all_routers = [
    auth.router,
    users.router,
    personnel.router,
    alerts.router,
    risk.router,
    analytics.router,
    audit.router,
    journals.router,
    assessments.router,
    settings_router.router,
    ai.router,
    voice.router,
    support.router,
    admin_console.router,
    hrms.router,
    biometrics.router,
    interventions.router,
]

# Mount under /api (for Android APK Retrofit client and Next.js)
for r in all_routers:
    app.include_router(r, prefix="/api")

# Mount under /api/v1 (for versioned API clients)
for r in all_routers:
    app.include_router(r, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
        "api_prefixes": ["/api", "/api/v1"],
    }


@app.get("/health/live")
def liveness():
    return {"status": "healthy", "service": "crpf-mhs-backend"}


def database_readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        logger.warning("Database readiness check failed: %s", type(error).__name__)
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {
        "status": "healthy",
        "service": "crpf-mhs-backend",
        "database": "connected",
    }


@app.get("/health")
def health():
    return database_readiness()


@app.get("/health/ready")
def readiness():
    return database_readiness()
