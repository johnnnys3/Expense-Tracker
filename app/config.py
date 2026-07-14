import os


class Config:
    # Required env vars — raises KeyError at import time if unset, by design
    # (fail fast rather than start the app with missing secrets/config).
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
