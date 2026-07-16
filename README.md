# Expense Tracker

A full-stack app for logging expenses and seeing totals by month/category. Flask + PostgreSQL API with JWT auth and a Celery-based account-deletion pipeline, plus a React SPA on top.

## Stack

- Flask (app-factory pattern, blueprints per resource)
- PostgreSQL + SQLAlchemy 2.0 (plain SQLAlchemy, not Flask-SQLAlchemy)
- Alembic for schema migrations (no `create_all()` — every schema change is a versioned migration)
- Flask-JWT-Extended for auth
- Flask-Limiter for auth rate limiting (Redis-backed, per-IP)
- Input validation on all write paths (`app/validation.py`)
- Celery + Redis for the account-purge background job
- React 19 + Vite + React Router frontend (see [Frontend](#frontend))

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

brew services start postgresql@17
brew services start redis
createdb expense_tracker

cp .env.example .env   # fill in SECRET_KEY, DATABASE_URL, CELERY_BROKER_URL

alembic upgrade head
python run.py           # or: flask --app run run
```

Run the background worker (only needed to actually purge soft-deleted accounts after their grace period):

```bash
celery -A app.celery_app worker --beat --loglevel=info
```

Run tests (uses an in-memory SQLite DB, no Postgres required):

```bash
pytest
```

95 tests cover auth, all four resources, input validation, rate limiting, and the purge job. GitHub Actions (`.github/workflows/ci.yml`) runs the full suite on every push and PR. The suite is order-dependent (shared session-scoped app/engine in `tests/conftest.py`), so it runs as a single whole-collection invocation — no `-n auto` or per-file sharding.

## API

All routes except `/auth/register` and `/auth/login` require `Authorization: Bearer <token>`.

| Method | Route | Notes |
|---|---|---|
| POST | `/auth/register` | Returns a token immediately (auto-login) |
| POST | `/auth/login` | |
| GET | `/auth/me` | |
| DELETE | `/auth/me` | Soft-delete: 30-day grace period before hard purge |
| POST / GET | `/categories` | Per-user; names unique per user, not globally |
| POST / GET | `/recurring-rules` | Pattern only — doesn't pre-generate `transactions` rows (see Schema below) |
| GET / PATCH / DELETE | `/recurring-rules/<id>` | 404 (not 403) if it belongs to another user |
| POST | `/transactions` | |
| GET | `/transactions` | Filters: `category_id`, `month=YYYY-MM`; pagination: `page`, `limit` (max 100) |
| GET / PATCH / DELETE | `/transactions/<id>` | 404 (not 403) if it belongs to another user |
| GET | `/transactions/summary` | Totals grouped by category; `month=YYYY-MM` optional |

## Schema

Four tables: `users`, `categories`, `transactions`, `recurring_rules`.

A few of the foreign-key decisions aren't the obvious defaults, so the reasoning is worth writing down:

- **`transactions.category_id` is `NOT NULL` at the app level, but `SET NULL` at the DB level.** Categorization is required when a transaction is created (the app validates this) — but the FK itself allows null, because the account-purge job hard-deletes categories, and the FK's `SET NULL` lets that happen without the database blocking on old transactions. `RESTRICT` was the first choice here, until the soft-delete feature needed to hard-delete categories out from under existing transactions.
- **`recurring_rules` don't pre-generate future `transactions` rows.** A rule is just a pattern (amount, category, frequency, start/end date); a separate process is expected to create the actual `transaction` row when an occurrence happens, with `recurring_rule_id` set. Pre-generating rows was the alternative, but it means editing a rule (e.g. a rent increase) requires hunting down and updating already-created future rows — keeping `transactions` as "what actually happened" avoids that.
- **`users` → `categories`/`recurring_rules`/`transactions` is `CASCADE`, but users aren't actually hard-deleted on request.** `DELETE /auth/me` soft-deletes (sets `deleted_at`); a daily Celery job hard-deletes accounts 30 days past that. When the purge finally runs, it deletes `recurring_rules` and `categories` outright (they can reveal spending patterns), but only scrubs `transactions.description` and lets the `SET NULL` FKs clear `user_id`/`category_id` — the transaction rows themselves survive, anonymized, rather than being deleted.
- **Ownership checks return 404, not 403.** Trying to read/update/delete another user's transaction returns the same "not found" as a nonexistent id — a 403 would confirm the id exists and just isn't yours.

## Frontend

React SPA in `frontend/` (Vite + React Router), talking to the API above.

```bash
cd frontend
npm install
npm run dev      # dev server (expects the API at the URL configured in src/api.js)
npm run build    # production build to dist/
```

Pages: Login, Dashboard, Transactions, Categories, Recurring Rules — one hook per resource (`useAuth`, `useTransactions`, `useCategories`, `useRecurringRules`) wrapping `api.js`. `ProtectedRoute` redirects to `/login` when there's no valid token.

## Deploy

Not hosted — this is a practice project. The `Dockerfile`, `railway.json`, and `.github/workflows/ci.yml` are kept as working reference for an API-only Railway deploy (managed Postgres + Redis; frontend would deploy separately to Vercel). The container runs `alembic upgrade head` then gunicorn. To run it locally:

```bash
docker build -t expense-tracker .
docker run -p 8000:8000 --env-file .env expense-tracker
```

## Known gaps

- No JWT blocklist — a token issued before a soft-delete stays valid until it naturally expires.
- The daily account-purge job is wired and tested, but the Celery beat scheduler only runs when started manually — there's no deployed scheduler triggering it on a real schedule.
