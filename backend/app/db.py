import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def _get_database_url():
    """Get the database URL from environment variable.
    
    Raises RuntimeError if the variable is unset or empty.
    """
    url = os.environ.get("TICKETER_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "TICKETER_DATABASE_URL environment variable is not set or is empty"
        )
    return url


# Read URL at import time and raise if missing/empty
_DATABASE_URL = _get_database_url()

engine = create_engine(_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Import app.models and create all tables."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
