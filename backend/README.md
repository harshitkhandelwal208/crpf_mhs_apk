# Sentinel Backend

FastAPI backend for the Sentinel personnel monitoring system.

## Setup

```bash
cd backend
pip install -r requirements.txt
python seed.py       # Seed development data (dev only)
uvicorn main:app --reload --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Test Users (Development Seed)

| Email | Password | Role |
|-------|----------|------|
| superadmin@sentinel.mil | sentinel-super-2024 | SUPER_ADMIN |
| admin@sentinel.mil | sentinel-admin-2024 | ADMIN |
| mhp@sentinel.mil | sentinel-mhp-2024 | MENTAL_HEALTH_PROFESSIONAL |
| supervisor@sentinel.mil | sentinel-super-2024 | SUPERVISOR |
| personnel1@sentinel.mil | sentinel-pers-2024 | PERSONNEL |
