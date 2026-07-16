import os


class Config:
    # Required env vars — raises KeyError at import time if unset, by design
    # (fail fast rather than start the app with missing secrets/config).
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]

    # On by default: a deploy that silently loses its rate limiting is worse
    # than one that fails loudly. Tests override this (see conftest).
    RATELIMIT_ENABLED = True
