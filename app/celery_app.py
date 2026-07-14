import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Standalone from Flask on purpose: the worker process never serves HTTP
# requests, so it only needs the DB layer, not create_app()/Flask itself.
from app.db import init_db  # noqa: E402

init_db(os.environ["DATABASE_URL"])

celery_app = Celery(
    "expense_tracker",
    broker=os.environ["CELERY_BROKER_URL"],
    include=["app.tasks"],
)

celery_app.conf.beat_schedule = {
    "purge-deleted-users-daily": {
        "task": "app.tasks.purge_deleted_users",
        "schedule": crontab(hour=3, minute=0),
    }
}
