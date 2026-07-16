# Expense Tracker

Flask API + React/Vite frontend. See [README.md](README.md) for the full stack.

## Deploy Configuration (configured by /setup-deploy)
- Platform: Railway (Dockerfile build)
- Production URL: TBD (set after first Railway deploy)
- Deploy workflow: auto-deploy on push to main (Railway watches the repo)
- Deploy status command: HTTP health check on `/`
- Merge method: squash
- Project type: web API (backend only on Railway; frontend deploys separately to Vercel)
- Post-deploy health check: `GET {production-url}/` → `{"status":"ok"}`

### Services (Railway)
- **web** — gunicorn serving `run:app` (Dockerfile). Start command runs
  `alembic upgrade head` then gunicorn.
- **Postgres** — Railway managed plugin. Provides `DATABASE_URL`.
- **Redis** — Railway managed plugin. Provides the URL for `CELERY_BROKER_URL`
  (rate-limiter storage reads it; falls back to `RATELIMIT_STORAGE_URI`).
- Celery worker/beat are NOT deployed (only job is a daily soft-delete purge —
  non-essential for the demo). Add later as separate services from this image.

### Required env vars (set in Railway web service)
- `SECRET_KEY` — Flask/JWT signing secret (config fails fast if unset)
- `DATABASE_URL` — from the Railway Postgres plugin
- `CELERY_BROKER_URL` — the Railway Redis URL (backs rate-limiter storage)
- `CORS_ORIGINS` — the deployed frontend origin(s), comma-separated

### Custom deploy hooks
- Pre-merge: `pytest tests/` (CI, `.github/workflows/ci.yml`)
- Deploy trigger: automatic on push to main (Railway)
- Deploy status: poll `GET /` until it returns 200 `{"status":"ok"}`
- Migrations: `alembic upgrade head`, run in the container start command

### CI
- `.github/workflows/ci.yml` runs `pytest tests/` as a single whole-suite
  invocation. The suite is order-dependent (shared session-scoped app/engine in
  `tests/conftest.py`) — do NOT add `-n auto` or per-file sharding until that's
  fixed. Tests self-provision env (in-memory SQLite, `memory://` broker); no
  Postgres/Redis needed in CI.

### Frontend (separate deploy — not yet configured)
- `frontend/` is a Vite SPA deployed to Vercel/Netlify (auto-builds on push).
- `frontend/src/api.js` currently hardcodes `http://localhost:5001` as the API
  base — this must point at the Railway API URL before the frontend goes live.
- Set the Railway web service's `CORS_ORIGINS` to the frontend's deployed origin.
