import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Retrieve the database URL from the environment.
# The variable must be set and non‑empty; otherwise we raise immediately.
_db_url = os.getenv("TICKETER_DATABASE_URL")
if not _db_url:
    raise RuntimeError("TICKETER_DATABASE_URL must be set and non‑empty")

# Create the SQLAlchemy engine.
engine = create_engine(_db_url, future=True)

# Declarative base class for model definitions.
class Base(DeclarativeBase):
    pass

# Session factory bound to the engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db() -> None:
    """Create all tables defined in the model modules.

    Importing ``app.models`` registers the model classes with ``Base``.
    ``Base.metadata.create_all`` then creates the tables in the database.
    """
    # Import models so that they are attached to Base.metadata.
    import importlib
    importlib.import_module("app.models")
    Base.metadata.create_all(engine)
