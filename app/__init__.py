from flask import Flask
from flask_jwt_extended import JWTManager

from app.config import Config
from app.db import init_db


def create_app(config_class=Config):
    # Application factory: builds and configures a Flask app instance.
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Wire up the DB engine/session using the configured connection string.
    init_db(app.config["SQLALCHEMY_DATABASE_URI"])

    # Signs/verifies tokens using app.config["JWT_SECRET_KEY"], which falls
    # back to SECRET_KEY if not set separately — no new config needed.
    JWTManager(app)

    # Imported here (not top-of-file) to avoid a circular import: auth.py
    # will need things from this package, and this package isn't finished
    # initializing until create_app() runs.
    from app.routes.auth import auth_bp
    from app.routes.categories import categories_bp
    from app.routes.transactions import transactions_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(transactions_bp)

    return app
