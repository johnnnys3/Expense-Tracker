from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]  # never store plaintext passwords
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    # None = active. Set on soft-delete; a Celery job hard-purges after a
    # grace period (see app/tasks.py). Login must reject non-null accounts.
    deleted_at: Mapped[datetime | None]


class Category(Base):
    __tablename__ = "categories"
    # Names only need to be unique per-user, not globally.
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deleting a user deletes their categories too.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]


class RecurringRule(Base):
    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # RESTRICT: block deleting a category while a recurring rule still uses it.
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # exact decimal, not float
    frequency: Mapped[str]  # e.g. "weekly" / "monthly"
    start_date: Mapped[date]
    end_date: Mapped[date | None]  # None = recurs indefinitely


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Nullable + SET NULL (not RESTRICT) so the account-purge job can
    # hard-delete a category without the DB blocking on old transactions —
    # deleting the category auto-clears this FK instead of erroring.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    # SET NULL: if the generating rule is deleted, the transaction record
    # (a historical fact) survives with this link cleared instead of being removed.
    recurring_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_rules.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    occurred_at: Mapped[date]  # date the expense happened
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)  # row insert time
