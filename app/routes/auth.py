from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import SessionLocal
from app.models import User
from app.validation import require_fields

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if error := require_fields(data, "email", "password"):
        return error
    email = data["email"]
    password = data["password"]

    with SessionLocal() as session:
        # Enforce unique email ourselves so we can return a clean 409
        # instead of surfacing a raw DB constraint-violation error.
        existing = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            return jsonify({"error": "email already registered"}), 409

        # Hash the password before it ever touches the DB — never store plaintext.
        user = User(email=email, password_hash=generate_password_hash(password))
        session.add(user)
        session.commit()

        # Log the new user straight in: issue a JWT with the user id as identity.
        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if error := require_fields(data, "email", "password"):
        return error
    email = data["email"]
    password = data["password"]

    with SessionLocal() as session:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        # Same error for "no such user", "wrong password", and "deleted
        # account" — avoids leaking account state to an unauthenticated caller.
        if (
            user is None
            or user.deleted_at is not None
            or not check_password_hash(user.password_hash, password)
        ):
            return jsonify({"error": "invalid email or password"}), 401

        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    # jwt_required() already validated the token; identity is the user id
    # we set in create_access_token above, stored as a string in the JWT.
    user_id = int(get_jwt_identity())

    with SessionLocal() as session:
        user = session.get(User, user_id)
        return jsonify({"id": user.id, "email": user.email})


@auth_bp.route("/me", methods=["DELETE"])
@jwt_required()
def soft_delete_me():
    user_id = int(get_jwt_identity())

    with SessionLocal() as session:
        user = session.get(User, user_id)
        user.deleted_at = datetime.utcnow()
        session.commit()
        # ponytail: a token issued before this call stays valid until it
        # naturally expires — no blocklist. Add one if immediate revocation
        # on delete ever matters.
        return "", 204
