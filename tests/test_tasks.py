from datetime import date, datetime, timedelta

import app.db as db_module
from app.models import Category, RecurringRule, Transaction, User
from app.tasks import GRACE_PERIOD_DAYS, purge_deleted_users


def _make_user(session, email, deleted_at=None):
    user = User(email=email, password_hash="x", deleted_at=deleted_at)
    session.add(user)
    session.flush()
    return user


def test_purge_deleted_users_skips_active_accounts(app_instance):
    with db_module.SessionLocal() as session:
        _make_user(session, "active@example.com")
        session.commit()

    purged_count = purge_deleted_users()
    assert purged_count == 0

    with db_module.SessionLocal() as session:
        assert session.query(User).count() == 1


def test_purge_deleted_users_skips_accounts_within_grace_period(app_instance):
    with db_module.SessionLocal() as session:
        _make_user(
            session,
            "recent@example.com",
            deleted_at=datetime.utcnow() - timedelta(days=1),
        )
        session.commit()

    purged_count = purge_deleted_users()
    assert purged_count == 0

    with db_module.SessionLocal() as session:
        assert session.query(User).count() == 1


def test_purge_deleted_users_removes_accounts_past_grace_period(app_instance):
    with db_module.SessionLocal() as session:
        _make_user(
            session,
            "old@example.com",
            deleted_at=datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS + 1),
        )
        session.commit()

    purged_count = purge_deleted_users()
    assert purged_count == 1

    with db_module.SessionLocal() as session:
        assert session.query(User).count() == 0


def test_purge_deleted_users_scrubs_related_data(app_instance):
    with db_module.SessionLocal() as session:
        user = _make_user(
            session,
            "full@example.com",
            deleted_at=datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS + 1),
        )
        category = Category(user_id=user.id, name="Groceries")
        session.add(category)
        session.flush()

        rule = RecurringRule(
            user_id=user.id,
            category_id=category.id,
            amount="9.99",
            frequency="monthly",
            start_date=date(2026, 1, 1),
            end_date=None,
        )
        session.add(rule)

        transaction = Transaction(
            user_id=user.id,
            category_id=category.id,
            amount="9.99",
            occurred_at=date(2026, 1, 1),
            description="sensitive note",
        )
        session.add(transaction)
        session.commit()
        transaction_id = transaction.id

    purge_deleted_users()

    with db_module.SessionLocal() as session:
        assert session.query(User).count() == 0
        assert session.query(Category).count() == 0
        assert session.query(RecurringRule).count() == 0

        # The transaction (a historical fact) survives the purge, but its
        # user/category links are cleared and free-text PII is scrubbed.
        remaining = session.get(Transaction, transaction_id)
        assert remaining is not None
        assert remaining.user_id is None
        assert remaining.category_id is None
        assert remaining.description is None


def test_purge_deleted_users_leaves_other_users_data_alone(app_instance):
    with db_module.SessionLocal() as session:
        _make_user(
            session,
            "purge-me@example.com",
            deleted_at=datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS + 1),
        )
        keep = _make_user(session, "keep-me@example.com")
        category = Category(user_id=keep.id, name="Rent")
        session.add(category)
        session.commit()

    purge_deleted_users()

    with db_module.SessionLocal() as session:
        assert session.query(User).count() == 1
        remaining_user = session.query(User).one()
        assert remaining_user.email == "keep-me@example.com"
        assert session.query(Category).count() == 1
