# Backend API image. The React/Vite frontend deploys separately (Vercel), so
# it's excluded via .dockerignore and never enters this image.
FROM python:3.12-slim

# PYTHONUNBUFFERED: stream logs straight to Railway (no stdout buffering).
# PYTHONDONTWRITEBYTECODE: skip .pyc files — pointless in an immutable image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps in their own layer so Docker only reinstalls when
# requirements.txt changes, not on every source edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT. Apply Alembic migrations to head, then exec gunicorn
# so it runs as PID 1 and receives SIGTERM directly on redeploy/shutdown.
# Migrations run in the start command (single web instance); if this service
# is ever scaled past one replica, move the migrate step to its own release
# job so replicas don't race on `alembic upgrade`.
CMD ["sh", "-c", "alembic upgrade head && exec gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} run:app"]
