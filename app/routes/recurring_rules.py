from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Category, RecurringRule
from app.validation import require_fields

recurring_rules_bp = Blueprint(
    "recurring_rules", __name__, url_prefix="/recurring-rules"
)


def _current_user_id() -> int:
    return int(get_jwt_identity())


def _serialize(r: RecurringRule) -> dict:
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

    with SessionLocal() as session:
        category = session.get(Category, data["category_id"])
        if category is None or category.user_id != user_id:
            return jsonify({"error": "invalid category_id"}), 400

        end_date = data.get("end_date")
        rule = RecurringRule(
            user_id=user_id,
            category_id=data["category_id"],
            amount=data["amount"],
            frequency=data["frequency"],
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(end_date) if end_date else None,
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

        if "category_id" in data:
            category = session.get(Category, data["category_id"])
            if category is None or category.user_id != user_id:
                return jsonify({"error": "invalid category_id"}), 400
            rule.category_id = data["category_id"]

        if "amount" in data:
            rule.amount = data["amount"]
        if "frequency" in data:
            rule.frequency = data["frequency"]
        if "start_date" in data:
            rule.start_date = date.fromisoformat(data["start_date"])
        if "end_date" in data:
            rule.end_date = date.fromisoformat(data["end_date"]) if data["end_date"] else None

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

        session.delete(rule)
        session.commit()
        return "", 204
