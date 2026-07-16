from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Category, RecurringRule
from app.validation import parse_amount, parse_date, require_fields

recurring_rules_bp = Blueprint(
    "recurring_rules", __name__, url_prefix="/recurring-rules"
)


def _current_user_id() -> int:
    return int(get_jwt_identity())


def _serialize(r: RecurringRule) -> dict:
    # amount as str (not float) to avoid losing Decimal precision in JSON.
    return {
        "id": r.id,
        "category_id": r.category_id,
        "amount": str(r.amount),
        "frequency": r.frequency,
        "start_date": r.start_date.isoformat(),
        "end_date": r.end_date.isoformat() if r.end_date else None,
    }


@recurring_rules_bp.route("", methods=["POST"])
@jwt_required()
def create_recurring_rule():
    user_id = _current_user_id()
    data = request.get_json()
    if error := require_fields(data, "category_id", "amount", "frequency", "start_date"):
        return error

    amount, error = parse_amount(data["amount"])
    if error:
        return error

    start_date, error = parse_date(data["start_date"], "start_date")
    if error:
        return error

    # end_date is optional: absent or null both mean "recurs indefinitely",
    # so only parse it when the caller actually supplied a value.
    end_date = None
    if data.get("end_date") is not None:
        end_date, error = parse_date(data["end_date"], "end_date")
        if error:
            return error

    with SessionLocal() as session:
        # Verify the category exists AND belongs to this user, same as
        # transactions — prevents attaching a rule to someone else's category.
        category = session.get(Category, data["category_id"])
        if category is None or category.user_id != user_id:
            return jsonify({"error": "invalid category_id"}), 400

        rule = RecurringRule(
            user_id=user_id,
            category_id=data["category_id"],
            amount=amount,
            frequency=data["frequency"],
            start_date=start_date,
            end_date=end_date,
        )
        session.add(rule)
        session.commit()
        return jsonify(_serialize(rule)), 201


@recurring_rules_bp.route("", methods=["GET"])
@jwt_required()
def list_recurring_rules():
    user_id = _current_user_id()

    with SessionLocal() as session:
        rules = session.execute(
            select(RecurringRule).where(RecurringRule.user_id == user_id)
        ).scalars().all()
        return jsonify([_serialize(r) for r in rules])


@recurring_rules_bp.route("/<int:rule_id>", methods=["GET"])
@jwt_required()
def get_recurring_rule(rule_id):
    user_id = _current_user_id()
    with SessionLocal() as session:
        rule = session.get(RecurringRule, rule_id)
        # 404 (not 403) for someone else's rule — same reasoning as transactions.
        if rule is None or rule.user_id != user_id:
            return jsonify({"error": "not found"}), 404
        return jsonify(_serialize(rule))


@recurring_rules_bp.route("/<int:rule_id>", methods=["PATCH"])
@jwt_required()
def update_recurring_rule(rule_id):
    user_id = _current_user_id()
    data = request.get_json()
    if error := require_fields(data):
        return error

    with SessionLocal() as session:
        rule = session.get(RecurringRule, rule_id)
        if rule is None or rule.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        # Partial update: only touch fields the caller actually sent.
        if "category_id" in data:
            category = session.get(Category, data["category_id"])
            if category is None or category.user_id != user_id:
                return jsonify({"error": "invalid category_id"}), 400
            rule.category_id = data["category_id"]

        if "amount" in data:
            amount, error = parse_amount(data["amount"])
            if error:
                return error
            rule.amount = amount
        if "frequency" in data:
            rule.frequency = data["frequency"]
        if "start_date" in data:
            start_date, error = parse_date(data["start_date"], "start_date")
            if error:
                return error
            rule.start_date = start_date
        if "end_date" in data:
            # Explicit null clears the end date (back to recurring forever).
            if data["end_date"] is None:
                rule.end_date = None
            else:
                end_date, error = parse_date(data["end_date"], "end_date")
                if error:
                    return error
                rule.end_date = end_date

        session.commit()
        return jsonify(_serialize(rule))


@recurring_rules_bp.route("/<int:rule_id>", methods=["DELETE"])
@jwt_required()
def delete_recurring_rule(rule_id):
    user_id = _current_user_id()
    with SessionLocal() as session:
        rule = session.get(RecurringRule, rule_id)
        if rule is None or rule.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        # No RESTRICT concern here: Transaction.recurring_rule_id is
        # ON DELETE SET NULL, so existing transactions just detach from the rule.
        session.delete(rule)
        session.commit()
        return "", 204
