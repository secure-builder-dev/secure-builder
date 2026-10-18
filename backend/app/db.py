import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Retrieve the database URL from the environment.
# The tests require a RuntimeError if the variable is missing or empty.
_db_url = os.getenv("TICKETER_DATABASE_URL")
if not _db_url:
    raise RuntimeError("TICKETER_DATABASE_URL environment variable must be set and non‑empty")

# Create the SQLAlchemy engine.
engine = create_engine(_db_url, future=True)

# Declarative base class for models.
class Base(DeclarativeBase):
    pass

# Session factory bound to the engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db() -> None:
    """Create all tables defined in the models.

    The function imports ``app.models`` to ensure model classes are registered
    with ``Base.metadata`` before calling ``create_all``.
    """
    # Import models so that their table definitions are attached to Base.metadata.
    import importlib
    importlib.import_module("app.models")
    Base.metadata.create_all(bind=engine)
