# Local AI integration

The Android app talks to the CRPF MHS FastAPI service. It does not call the model directly.

## Android to backend

- Emulator base URL: `http://10.0.2.2:8000/`
- Physical device: change `BASE_URL` in `app/src/main/java/com/example/myapplication/api/ApiClient.java` to the development machine LAN address, for example `http://192.168.1.20:8000/`.
- The backend must be reachable on the network, not only bound to `127.0.0.1`.
- Local HTTP is enabled for development only. Use HTTPS for staging/production.

## Backend routes used by Android

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/users/me`
- `POST /api/ai/chat`
- `POST /api/journals`
- `POST /api/voice/transcribe` as multipart field `audio`
- `POST /api/support/request`

Bearer access tokens are added by `AuthInterceptor`. Expired access tokens are refreshed through `/api/auth/refresh` by `TokenAuthenticator`.

## Local model provider

The backend owns safety checks, risk escalation, audit logging, and consent boundaries. The model should remain behind the backend provider abstraction.

If the teammate's model exposes an OpenAI-compatible API, configure the backend environment without committing secrets:

```env
AI_PROVIDER=openai
AI_BASE_URL=http://127.0.0.1:11434/v1
AI_MODEL=your-local-model
AI_API_KEY=local-development-value
```

For a custom non-OpenAI-compatible model, implement `AIProvider` in `backend/app/ai/providers.py` and update `get_ai_provider()`. Keep these methods available:

- `chat(message, history)`
- `analyze_journal(text)`
- `transcribe(content, mime_type)`

The server's deterministic safety layer must remain in place. The model must not diagnose, make clinical claims, or receive credentials from the Android client.

## Current Android behavior

- AI companion sends a safe starter message and displays the server response.
- Journal entries are submitted as `SUBMITTED` with a review-safe failure message if the request does not complete.
- Voice upload and support request Retrofit methods are ready for the remaining UI actions.
- Android diagnostics pass. A Gradle build still requires a configured JDK and `JAVA_HOME`.

## Employee app and admin website boundary

- The Android app is personnel-only. It has no admin login, admin navigation, admin API methods, or admin data views.
- After login, Android fetches `/api/users/me`; any role other than `PERSONNEL` is immediately signed out and its tokens are cleared.
- The CRPF MHS website remains the admin surface. It should use the same FastAPI service and the `/api/admin/*` routes for audited administrator workflows.
- Employee data reaches the website through the shared backend database and API. The Android app submits journals, assessments, AI conversations, voice transcripts, consent, and support requests to the backend; authorized website users can then see only the data allowed by RBAC and audit policy.
- Do not call `/api/admin/*` from Android and do not expose admin credentials or model credentials in the APK.
