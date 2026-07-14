from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Populated by init_db() once the app config is available; None until then.
engine = None
SessionLocal = None


class Base(DeclarativeBase):
    # Shared declarative base — all ORM models inherit from this so their
    # tables register under one MetaData (used by Alembic autogenerate).
    pass


def init_db(database_uri: str) -> None:
    global engine, SessionLocal
    engine = create_engine(database_uri)
    # Session factory: call SessionLocal() to get a new DB session bound to this engine.
    SessionLocal = sessionmaker(bind=engine)
