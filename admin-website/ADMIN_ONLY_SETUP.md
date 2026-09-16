# CRPF MHS Admin Website Copy

This folder is a standalone copy of the reference CRPF MHS website, kept beside the Android employee app for integration work.

## Scope

- This copy is restricted to administrator sign-in and the admin console.
- Personnel accounts must use the Android employee app.
- Public landing, registration, and employee routes are not available through the active entry flow.
- The backend and database files are included so the website can use the same shared service contract.

## Included

- Next.js website source in `src/`
- FastAPI backend in `backend/`
- Prisma/database configuration
- Tests, docs, styling, and build configuration
- `.env.example` only

Generated dependencies, build output, Git metadata, caches, virtual environments, and `.env` secrets were intentionally excluded. Install dependencies locally before running the copy.

## Run the website

```powershell
npm install
npm run dev
```

The admin website is then available at `http://localhost:3000`.

## Run the backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Configure the website environment from `.env.example`. Never commit production secrets.

## Roles

The active login accepts only:

- `ADMIN`
- `SUPER_ADMIN`
- `MENTAL_HEALTH_PROFESSIONAL`
- `SUPERVISOR`

The backend must continue enforcing these roles and all `/api/admin/*` permissions. Client-side routing is only a convenience guard.
