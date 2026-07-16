import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify

# Numeric(10,2) tops out here. Postgres raises on overflow but SQLite silently
# stores the oversized value, so the bound is enforced in app code to keep the
# two backends (CI vs. production) behaving identically.
_MAX_AMOUNT = Decimal("99999999.99")

# Deliberately loose: something@something.something with no whitespace.
# Not RFC 5322 — email is only a login key here, nothing sends mail, so
# this exists to reject obvious junk rather than to guarantee deliverability.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email):
    # Same contract as require_fields: None means valid.
    if not isinstance(email, str) or not _EMAIL_RE.match(email):
        return jsonify({"error": "email is not a valid email address"}), 400
    return None


def parse_amount(value):
    # Returns (amount, None) or (None, error) — parsers need to hand back a
    # value, so they return a pair rather than require_fields' bare error.
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, (jsonify({"error": "amount must be a number"}), 400)
    # Decimal("NaN") parses successfully but makes every comparison below
    # raise InvalidOperation, so it has to be rejected before them.
    if not amount.is_finite():
        return None, (jsonify({"error": "amount must be a finite number"}), 400)
    # Expenses are positive; a negative would silently skew /summary totals.
    if amount < 0:
        return None, (jsonify({"error": "amount must not be negative"}), 400)
    if amount > _MAX_AMOUNT:
        return None, (jsonify({"error": f"amount must not exceed {_MAX_AMOUNT}"}), 400)
    return amount, None


def parse_date(value, field):
    # Same (value, error) pair as parse_amount. `field` names the offending
    # key so callers with several dates (recurring rules) say which one broke.
    try:
        return date.fromisoformat(value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{field} must be an ISO 8601 date (YYYY-MM-DD)"}), 400)


def parse_month(value):
    # "YYYY-MM" -> ((start, end), None), a half-open range for filtering.
    # Returns the range rather than the parts because both callers only ever
    # want the bounds, including the December roll-over into the next year.
    try:
        year_str, month_str = value.split("-")
        year, month = int(year_str), int(month_str)
        start = date(year, month, 1)
    except (AttributeError, TypeError, ValueError):
        return None, (jsonify({"error": "month must be formatted YYYY-MM"}), 400)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (start, end), None


def require_fields(data, *fields):
    # Callers use `if error := require_fields(data, ...): return error` —
    # None means "valid", anything else is a ready-to-return Flask response.
    if not data:
        return jsonify({"error": "request body must be JSON"}), 400
    missing = [f for f in fields if f not in data]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
    return None
