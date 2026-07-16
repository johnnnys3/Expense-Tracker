from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Category, Transaction
from app.validation import parse_amount, parse_date, parse_month, require_fields

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _current_user_id() -> int:
    return int(get_jwt_identity())


def _serialize(t: Transaction) -> dict:
    # amount as str (not float) to avoid losing Decimal precision in JSON.
    return {
        "id": t.id,
        "amount": str(t.amount),
        "category_id": t.category_id,
        "occurred_at": t.occurred_at.isoformat(),
        "description": t.description,
        "recurring_rule_id": t.recurring_rule_id,
    }


@transactions_bp.route("", methods=["POST"])
@jwt_required()
def create_transaction():
    user_id = _current_user_id()
    data = request.get_json()
    if error := require_fields(data, "category_id", "amount", "occurred_at"):
        return error

    amount, error = parse_amount(data["amount"])
    if error:
        return error

    occurred_at, error = parse_date(data["occurred_at"], "occurred_at")
    if error:
        return error

    with SessionLocal() as session:
        # Verify the category exists AND belongs to this user — otherwise a
        # user could attach their transaction to someone else's category.
        category = session.get(Category, data["category_id"])
        if category is None or category.user_id != user_id:
            return jsonify({"error": "invalid category_id"}), 400

        transaction = Transaction(
            user_id=user_id,
            category_id=data["category_id"],
            amount=amount,
            occurred_at=occurred_at,
            description=data.get("description"),
        )
        session.add(transaction)
        session.commit()
        return jsonify(_serialize(transaction)), 201


@transactions_bp.route("", methods=["GET"])
@jwt_required()
def list_transactions():
    user_id = _current_user_id()
    category_id = request.args.get("category_id", type=int)
    month = request.args.get("month")  # "YYYY-MM"
    page = request.args.get("page", default=1, type=int)
    # Cap the page size so a client can't force an unbounded query.
    limit = min(request.args.get("limit", default=20, type=int), 100)

    with SessionLocal() as session:
        query = select(Transaction).where(Transaction.user_id == user_id)

        if category_id is not None:
            query = query.where(Transaction.category_id == category_id)

        if month is not None:
            bounds, error = parse_month(month)
            if error:
                return error
            start, end = bounds
            query = query.where(
                Transaction.occurred_at >= start, Transaction.occurred_at < end
            )

        query = (
            query.order_by(Transaction.occurred_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        transactions = session.execute(query).scalars().all()
        return jsonify([_serialize(t) for t in transactions])


@transactions_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    user_id = _current_user_id()
    month = request.args.get("month")  # "YYYY-MM"

    with SessionLocal() as session:
        # Inner join means categories with zero transactions in the period
        # are silently omitted from the summary rather than showing a 0 total.
        query = (
            select(Category.id, Category.name, func.sum(Transaction.amount))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(Transaction.user_id == user_id)
            .group_by(Category.id, Category.name)
            .order_by(Category.name)
        )

        if month is not None:
            bounds, error = parse_month(month)
            if error:
                return error
            start, end = bounds
            query = query.where(
                Transaction.occurred_at >= start, Transaction.occurred_at < end
            )

        rows = session.execute(query).all()
        return jsonify(
            [
                {"category_id": cat_id, "category_name": name, "total": str(total)}
                for cat_id, name, total in rows
            ]
        )


@transactions_bp.route("/<int:transaction_id>", methods=["GET"])
@jwt_required()
def get_transaction(transaction_id):
    user_id = _current_user_id()
    with SessionLocal() as session:
        transaction = session.get(Transaction, transaction_id)
        # Treat "exists but belongs to someone else" the same as "doesn't
        # exist" (404, not 403) — avoids confirming other users' record ids.
        if transaction is None or transaction.user_id != user_id:
            return jsonify({"error": "not found"}), 404
        return jsonify(_serialize(transaction))


@transactions_bp.route("/<int:transaction_id>", methods=["PATCH"])
@jwt_required()
def update_transaction(transaction_id):
    user_id = _current_user_id()
    data = request.get_json()
    if error := require_fields(data):
        return error

    with SessionLocal() as session:
        transaction = session.get(Transaction, transaction_id)
        if transaction is None or transaction.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        # Partial update: only touch fields the caller actually sent.
        if "category_id" in data:
            category = session.get(Category, data["category_id"])
            if category is None or category.user_id != user_id:
                return jsonify({"error": "invalid category_id"}), 400
            transaction.category_id = data["category_id"]

        if "amount" in data:
            amount, error = parse_amount(data["amount"])
            if error:
                return error
            transaction.amount = amount
        if "occurred_at" in data:
            occurred_at, error = parse_date(data["occurred_at"], "occurred_at")
            if error:
                return error
            transaction.occurred_at = occurred_at
        if "description" in data:
            transaction.description = data["description"]

        session.commit()
        return jsonify(_serialize(transaction))


@transactions_bp.route("/<int:transaction_id>", methods=["DELETE"])
@jwt_required()
def delete_transaction(transaction_id):
    user_id = _current_user_id()
    with SessionLocal() as session:
        transaction = session.get(Transaction, transaction_id)
        if transaction is None or transaction.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        session.delete(transaction)
        session.commit()
        return "", 204
