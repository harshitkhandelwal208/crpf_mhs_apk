"""
Sentinel Backend - FastAPI Application Entry Point
Dual-mounted for Android Mobile APK (/api) and Admin Web Console (/api and /api/v1)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models  # Ensures all models are registered with Base metadata
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
)

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sentinel Personnel Stress & Welfare Monitoring System API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "crpf-mhs-backend"}
