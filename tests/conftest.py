import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# Read at import time by app.celery_app; never actually dialed in tests
# since we invoke task functions directly instead of going through Celery.
os.environ.setdefault("CELERY_BROKER_URL", "memory://")

import pytest
from sqlalchemy import event

import app.db as db_module
from app import create_app
from app.config import Config
from app.db import Base


class TestConfig(Config):
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Must stay enabled: Flask-Limiter only registers its enforcement hook
    # when enabled at init_app, and init_app can't run again once the
    # session-scoped app has served a request. So the limiter is live for the
    # whole suite and the reset_rate_limiter fixture clears its counters
    # between tests, so ~50 same-IP logins across the suite don't pile up.
    RATELIMIT_ENABLED = True


@pytest.fixture(scope="session")
def app_instance():
    # Route modules do `from app.db import SessionLocal` at import time.
    # Python only runs that import once per process (module caching), so
    # create_app() must only be called once here — a per-test engine swap
    # would leave already-imported route modules pointing at a stale
    # SessionLocal. Instead, build the app/engine once for the whole
    # session and reset table contents between tests (see `db` fixture).
    flask_app = create_app(TestConfig)
    engine = db_module.engine

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    # app.celery_app calls init_db() itself at import time (it runs
    # standalone from Flask, without create_app()), which — same as the
    # route-module problem above — leaves any already-imported app.tasks
    # bound to a different, table-less engine. Repoint it at the one
    # actually wired up here.
    try:
        import app.tasks as tasks_module

        tasks_module.SessionLocal = db_module.SessionLocal
    except ImportError:
        pass

    yield flask_app

    engine.dispose()


@pytest.fixture(autouse=True)
def db(app_instance):
    engine = db_module.engine
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter(app_instance):
    # The limiter is enabled suite-wide (see TestConfig) and its storage is
    # shared across the session app, so counts would otherwise carry from one
    # test into the next. Clear them before each test: the rate-limit tests
    # can then count exactly, and every other test starts with a fresh
    # allowance no matter how many logins ran before it.
    from app.extensions import limiter

    with app_instance.app_context():
        limiter.reset()


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture()
def register_user(client):
    def _register(email="user@example.com", password="hunter2"):
        resp = client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        return resp

    return _register


@pytest.fixture()
def auth_headers(client, register_user):
    def _auth_headers(email="user@example.com", password="hunter2"):
        register_user(email, password)
        resp = client.post("/auth/login", json={"email": email, "password": password})
        token = resp.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
