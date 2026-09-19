# Sentinel Backend & CRPF MHS AI Service

FastAPI backend for the Sentinel Personnel Stress and Welfare Monitoring System, fully integrating the **HK Neural Framework** (`harshitkhandelwal208/hk`) and the **Mental Welfare Intelligence Models** (`Mental_Health_Ui`).

---

## Key Capabilities

1. **HK Neural Pipeline Architecture**:
   - `CompositePipeline`: High-level heterogeneous model orchestrator coordinating STT, Intent & Sentiment analysis, and Causal LLM generation.
   - `ContextWindowManager`: Dynamic token budgeting and `middle_out` context truncation.
   - `PipelineContext`: Blackboard context state tracking stage execution and signals.

2. **Mental Welfare Intelligence**:
   - **3-Tier Routing**: 66M DistilBERT sequence classification + VADER lexical polarity sentiment -> blended 0-100 morale score.
   - **Deterministic Crisis Safety Net**: Immediate escalation for self-harm / suicidal ideation triggers.
   - **RAG Clinical Vector Search**: Cosine similarity matching over 24 clinical skills and protocols (`data/rag_db.json` and `data/mental_health_skill/`).
   - **Longitudinal Trajectory Tracker**: Moving trend detection across sessions (`STABLE`, `DECLINING`, `RAPIDLY DECLINING`, `IMPROVING`, `RAPIDLY IMPROVING`).
   - **Whisper Speech-to-Text**: Edge audio note transcription.

3. **Dual-Route API Contract**:
   - All routes are dual-mounted under `/api` (for Android APK Retrofit client) and `/api/v1` (for versioned web clients).

---

## Setup & Run Locally

```bash
cd backend
python -m pip install -r requirements.txt
python seed.py       # Initialize and seed database
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health Check: http://localhost:8000/health

---

## Running Integration Tests

Run the full 14-test suite covering Android Retrofit contracts, AI companion turns, RAG retrieval, journal submissions, voice uploads, support requests, and risk engine alert escalations:

```bash
cd backend
python test_backend_integration.py
```

---

## Test Credentials (Development Seed)

| Email | Password | Role | Surface |
|---|---|---|---|
| `personnel1@sentinel.mil` | `sentinel-pers-2024` | PERSONNEL | Android Mobile App |
| `admin@sentinel.mil` | `sentinel-admin-2024` | ADMIN | Web Admin Console |
| `mhp@sentinel.mil` | `sentinel-mhp-2024` | MENTAL_HEALTH_PROFESSIONAL | Web Admin Console (Clinical) |
| `supervisor@sentinel.mil` | `sentinel-super-2024` | SUPERVISOR | Web Admin Console |
| `superadmin@sentinel.mil` | `sentinel-super-2024` | SUPER_ADMIN | Web Admin Console |

---

## Endpoints Used by Android Client

- `POST /api/auth/login`: Authenticate personnel, return access & refresh JWTs.
- `POST /api/auth/refresh`: Rotate refresh token, issue fresh access token.
- `GET /api/users/me`: Personnel profile (`id`, `name`, `email`, `role: PERSONNEL`, `onboarding_complete: true`).
- `POST /api/ai/chat`: AI companion chat with RAG context, morale score, and safety escalation.
- `POST /api/journals`: Daily private reflection with automatic AI wellbeing analysis.
- `POST /api/voice/transcribe`: Audio transcription with Whisper STT.
- `POST /api/support/request`: Submit routine or urgent support requests.
- `GET /api/emergency-contacts`: 24/7 force welfare helplines & unit medical contacts.
- `GET /api/resources`: Educational wellbeing resources.
