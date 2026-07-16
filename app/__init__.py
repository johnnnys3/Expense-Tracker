import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.db import init_db
from app.extensions import limiter


def create_app(config_class=Config):
    # Application factory: builds and configures a Flask app instance.
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Behind Railway's proxy the socket peer is the proxy, not the client, so
    # request.remote_addr would be the same for everyone — and rate limiting
    # keys on it. Trust one layer of X-Forwarded-For so remote_addr is the
    # real client. x_for=1 assumes exactly one proxy in front; raise it only
    # if more are added, since each trusted hop is one a client could spoof.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    # Wire up the DB engine/session using the configured connection string.
    init_db(app.config["SQLALCHEMY_DATABASE_URI"])

    # Signs/verifies tokens using app.config["JWT_SECRET_KEY"], which falls
    # back to SECRET_KEY if not set separately — no new config needed.
    JWTManager(app)

    # Reads RATELIMIT_* from app.config. Enforcement is a before_request hook
    # registered here, so it can only be wired when enabled at init time.
    limiter.init_app(app)

    # The frontend is deployed separately (Vercel), so in production the API
    # must allow its origin. CORS_ORIGINS is a comma-separated env list; it
    # falls back to the local Vite dev server so local dev needs no config.
    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    CORS(app, origins=[o.strip() for o in cors_origins.split(",") if o.strip()])

    # Imported here (not top-of-file) to avoid a circular import: auth.py
    # will need things from this package, and this package isn't finished
    # initializing until create_app() runs.
    from app.routes.auth import auth_bp
    from app.routes.categories import categories_bp
    from app.routes.recurring_rules import recurring_rules_bp
    from app.routes.transactions import transactions_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(recurring_rules_bp)
    app.register_blueprint(transactions_bp)

    @app.get("/")
    def health():
        return {"status": "ok"}

    return app
