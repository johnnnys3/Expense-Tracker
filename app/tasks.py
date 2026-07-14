from datetime import datetime, timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import Category, RecurringRule, Transaction, User

GRACE_PERIOD_DAYS = 30


@celery_app.task(name="app.tasks.purge_deleted_users")
def purge_deleted_users() -> int:
    cutoff = datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS)

    with SessionLocal() as session:
        due = session.execute(
            select(User.id).where(
                User.deleted_at.isnot(None), User.deleted_at <= cutoff
            )
        ).scalars().all()

        for user_id in due:
            _purge_user(session, user_id)

        session.commit()
        return len(due)


def _purge_user(session, user_id: int) -> None:
    # Scrub free-text PII the DB can't clear on its own.
    session.execute(
        Transaction.__table__.update()
        .where(Transaction.user_id == user_id)
        .values(description=None)
    )
    # RecurringRule -> Category is RESTRICT, so rules must go before categories.
    session.execute(
        RecurringRule.__table__.delete().where(RecurringRule.user_id == user_id)
    )
    # Deleting categories/user auto-clears transactions.category_id/user_id
    # via their ON DELETE SET NULL constraints — no manual nulling needed.
    session.execute(Category.__table__.delete().where(Category.user_id == user_id))
    session.execute(User.__table__.delete().where(User.id == user_id))
