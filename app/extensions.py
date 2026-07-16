import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Lives in its own module so route blueprints and create_app() can both import
# the limiter without importing each other (same circular-import problem the
# blueprint imports in create_app() work around).
#
# Storage defaults to the Celery broker's Redis: rate limits must be shared
# across processes, and an in-memory counter would give each worker its own
# allowance. Falls back to in-memory only so tests/local runs work without
# Redis — see RATELIMIT_ENABLED, which turns the limiter off in tests anyway.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI")
    or os.environ.get("CELERY_BROKER_URL")
    or "memory://",
)
