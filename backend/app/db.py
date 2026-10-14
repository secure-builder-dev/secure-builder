import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _get_database_url():
    """Get the database URL from environment variable.
    
    Raises RuntimeError if TICKETER_DATABASE_URL is unset or empty.
    """
    url = os.environ.get("TICKETER_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "TICKETER_DATABASE_URL environment variable is not set or is empty"
        )
    return url


# Read database URL at import time and raise if missing
_DATABASE_URL = _get_database_url()

engine = create_engine(_DATABASE_URL)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Initialize the database by creating all tables.
    
    Imports app.models to register all model classes with Base,
    then creates all tables defined in those models.
    """
    from app import models  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
