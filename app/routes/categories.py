from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Category
from app.validation import require_fields

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


@categories_bp.route("", methods=["POST"])
@jwt_required()
def create_category():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if error := require_fields(data, "name"):
        return error

    with SessionLocal() as session:
        # Enforce the per-user uniqueness ourselves (see Category.__table_args__)
        # so we can return a clean 409 instead of a raw DB constraint error.
        existing = session.execute(
            select(Category).where(
                Category.user_id == user_id, Category.name == data["name"]
            )
        ).scalar_one_or_none()
        if existing is not None:
            return jsonify({"error": "category already exists"}), 409

        category = Category(user_id=user_id, name=data["name"])
        session.add(category)
        session.commit()
        return jsonify({"id": category.id, "name": category.name}), 201


@categories_bp.route("/<int:category_id>", methods=["PATCH"])
@jwt_required()
def rename_category(category_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if error := require_fields(data, "name"):
        return error

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if category is None or category.user_id != user_id:
            return jsonify({"error": "not found"}), 404

        # Enforce per-user uniqueness ourselves (see create_category) so we
        # can return a clean 409 instead of a raw DB constraint error.
        existing = session.execute(
            select(Category).where(
                Category.user_id == user_id,
                Category.name == data["name"],
                Category.id != category_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return jsonify({"error": "category already exists"}), 409

        category.name = data["name"]
        session.commit()
        return jsonify({"id": category.id, "name": category.name})


@categories_bp.route("", methods=["GET"])
@jwt_required()
def list_categories():
    user_id = int(get_jwt_identity())

    with SessionLocal() as session:
        # Scoped to the caller only — never expose other users' categories.
        categories = session.execute(
            select(Category).where(Category.user_id == user_id)
        ).scalars().all()
        return jsonify([{"id": c.id, "name": c.name} for c in categories])
