import os
import sys
import importlib
import subprocess
import pytest
from sqlalchemy import inspect, Column
from sqlalchemy.orm import DeclarativeBase


def test_models_define_ticket_with_exact_columns():
    """Clause 3 – ``app.models`` must define a ``Ticket`` model with the exact
    schema required.
    """
    # Ensure the DB env var is set so that importing ``app.models`` does not raise
    os.environ["TICKETER_DATABASE_URL"] = "sqlite:///:memory:"
    # Import the module fresh
    if "app.models" in sys.modules:
        del sys.modules["app.models"]
    models = importlib.import_module("app.models")

    # The model must be named Ticket and inherit from the shared Base
    assert hasattr(models, "Ticket"), "app.models must define a Ticket class"
    Ticket = models.Ticket
    assert issubclass(Ticket, models.Base), "Ticket must inherit from Base"
    # Table name
    assert getattr(Ticket, "__tablename__", None) == "tickets", "Ticket table name must be 'tickets'"

    # Inspect columns
    cols = {c.name: c for c in Ticket.__table__.columns}
    expected = {
        "id": ("Integer", True, False),
        "title": ("String", False, False),
        "details": ("String", False, True),
        "priority": ("String", False, False),
        "due": ("Date", False, True),
        "status": ("String", False, False),
        "filed_by": ("String", False, False),
        "assigned_to": ("String", False, False),
        "created_at": ("DateTime", False, False),
        "updated_at": ("DateTime", False, False),
    }
    for name, (type_name, primary, nullable) in expected.items():
        assert name in cols, f"Column '{name}' missing in Ticket"
        col = cols[name]
        # Type name check (SQLAlchemy types may be wrapped, compare class name)
        assert col.type.__class__.__name__ == type_name, f"Column '{name}' should be of type {type_name}"
        assert col.primary_key == primary, f"Column '{name}' primary_key should be {primary}"
        assert col.nullable == nullable, f"Column '{name}' nullable should be {nullable}"
    # Check default for details column
    details_col = cols["details"]
    assert details_col.default is not None, "details column must have a default"
    # The default should be an empty string (SQLAlchemy may store as a callable)
    default_val = details_col.default.arg if hasattr(details_col.default, "arg") else details_col.default
    assert default_val == "" or (callable(default_val) and default_val() == ""), "details default must be empty string"

    # Clean up import cache
    del sys.modules["app.models"]


def test_db_raises_when_env_unset_or_empty():
    """Clause 1 – ``app.db`` must raise RuntimeError when TICKETER_DATABASE_URL is unset or empty."""
    # Helper to run import in a subprocess with given env
    def run_import(env):
        return subprocess.run(
            [sys.executable, "-c", "import importlib; importlib.import_module('app.db')"],
            env=env,
            capture_output=True,
            text=True,
        )

    # Case 1: variable unset
    env_unset = os.environ.copy()
    env_unset.pop("TICKETER_DATABASE_URL", None)
    result_unset = run_import(env_unset)
    assert result_unset.returncode != 0, "Import should fail when env var is missing"
    assert "RuntimeError" in (result_unset.stderr + result_unset.stdout)

    # Case 2: variable empty string
    env_empty = os.environ.copy()
    env_empty["TICKETER_DATABASE_URL"] = ""
    result_empty = run_import(env_empty)
    assert result_empty.returncode != 0, "Import should fail when env var is empty"
    assert "RuntimeError" in (result_empty.stderr + result_empty.stdout)


def test_db_defines_engine_base_and_init_db():
    """Clause 2 – ``app.db`` defines engine, Base, SessionLocal and init_db() correctly."""
    # Ensure env var is set to an in‑memory SQLite DB
    os.environ["TICKETER_DATABASE_URL"] = "sqlite:///:memory:"
    # Remove any previously loaded module
    if "app.db" in sys.modules:
        del sys.modules["app.db"]
    db = importlib.import_module("app.db")

    # Check required attributes exist
    assert hasattr(db, "engine"), "app.db must define engine"
    assert hasattr(db, "Base"), "app.db must define Base"
    assert hasattr(db, "SessionLocal"), "app.db must define SessionLocal"
    assert hasattr(db, "init_db"), "app.db must define init_db"

    # Base must be subclass of DeclarativeBase
    assert issubclass(db.Base, DeclarativeBase), "Base must subclass DeclarativeBase"

    # engine should be an instance of sqlalchemy.Engine (type check via inspect)
    from sqlalchemy import Engine
    assert isinstance(db.engine, Engine), "engine must be a SQLAlchemy Engine"

    # SessionLocal should be a sessionmaker bound to the engine
    from sqlalchemy.orm import sessionmaker
    assert isinstance(db.SessionLocal, sessionmaker), "SessionLocal must be a sessionmaker"
    # The bind of the sessionmaker should be the same engine
    assert db.SessionLocal.kw['bind'] is db.engine, "SessionLocal must be bound to engine"

    # init_db should create tables; call it and verify the tickets table exists
    db.init_db()
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    assert "tickets" in tables, "init_db should create the tickets table"

    # Clean up import cache
    del sys.modules["app.db"]
    # Also ensure models can be imported after init_db
    if "app.models" in sys.modules:
        del sys.modules["app.models"]
    importlib.import_module("app.models")
    # Clean up models import cache as well
    del sys.modules["app.models"]
    
    # Reset env var for other tests
    os.environ.pop("TICKETER_DATABASE_URL", None)

    # End of test
    
    # Note: The test intentionally does not assert the exact contents of the tables beyond existence,
    # as that is covered by the Ticket model test (clause 3).

    # Clean up any leftover modules
    for mod in ["app.db", "app.models"]:
        if mod in sys.modules:
            del sys.modules[mod]

    # Ensure no side‑effects remain
    os.environ.pop("TICKETER_DATABASE_URL", None)

    # End of test function
    
    # (No return needed)
    
    # End of file
