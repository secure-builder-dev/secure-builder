import os
import sys
import subprocess
import pytest
from datetime import datetime, timezone

# Import application modules directly (environment is set by the test harness)
from app import db as app_db
from app.models import Ticket
from app.rules import USERS, ticket_to_dict, create_ticket


def test_models_define_ticket_with_exact_columns():
    """Clause 3 – ``app.models`` must define a ``Ticket`` model with the exact
    schema required.
    """
    # The model must be named Ticket and inherit from the shared Base
    assert hasattr(Ticket, "__tablename__"), "Ticket must have __tablename__"
    assert Ticket.__tablename__ == "tickets", "Ticket table name must be 'tickets'"

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
        assert col.type.__class__.__name__ == type_name, f"Column '{name}' should be of type {type_name}"
        assert col.primary_key == primary, f"Column '{name}' primary_key should be {primary}"
        assert col.nullable == nullable, f"Column '{name}' nullable should be {nullable}"
    # Check default for details column
    details_col = cols["details"]
    assert details_col.default is not None, "details column must have a default"
    default_val = details_col.default.arg if hasattr(details_col.default, "arg") else details_col.default
    assert default_val == "" or (callable(default_val) and default_val() == ""), "details default must be empty string"


def test_db_raises_when_env_unset_or_empty():
    """Clause 1 – ``app.db`` must raise RuntimeError when TICKETER_DATABASE_URL is unset or empty."""
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
    # Check required attributes exist
    assert hasattr(app_db, "engine"), "app.db must define engine"
    assert hasattr(app_db, "Base"), "app.db must define Base"
    assert hasattr(app_db, "SessionLocal"), "app.db must define SessionLocal"
    assert hasattr(app_db, "init_db"), "app.db must define init_db"

    # Base must be subclass of DeclarativeBase
    from sqlalchemy.orm import DeclarativeBase
    assert issubclass(app_db.Base, DeclarativeBase), "Base must subclass DeclarativeBase"

    # engine should be an instance of sqlalchemy.Engine
    from sqlalchemy import Engine
    assert isinstance(app_db.engine, Engine), "engine must be a SQLAlchemy Engine"

    # SessionLocal should be a sessionmaker bound to the engine
    from sqlalchemy.orm import sessionmaker
    assert isinstance(app_db.SessionLocal, sessionmaker), "SessionLocal must be a sessionmaker"
    assert app_db.SessionLocal.kw["bind"] is app_db.engine, "SessionLocal must be bound to engine"

    # init_db should create tables; call it and verify the tickets table exists
    app_db.init_db()
    from sqlalchemy import inspect
    inspector = inspect(app_db.engine)
    tables = inspector.get_table_names()
    assert "tickets" in tables, "init_db should create the tickets table"


def test_rules_users_and_ticket_to_dict_structure(db):
    """Clause 1 – ``app.rules`` defines USERS and ticket_to_dict correctly."""
    # USERS must be a tuple with exactly 'her' and 'him'
    assert isinstance(USERS, tuple), "USERS must be a tuple"
    assert USERS == ("her", "him"), "USERS must be ('her', 'him')"

    # Create a ticket manually to test ticket_to_dict
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        title="Test",
        details="Details",
        priority="low",
        due=now.date(),
        status="open",
        filed_by="her",
        assigned_to="him",
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    d = ticket_to_dict(ticket)
    # All expected keys present
    expected_keys = {"id", "title", "details", "priority", "due", "status", "filed_by", "assigned_to", "created_at", "updated_at"}
    assert set(d.keys()) == expected_keys
    # Types and formats
    assert isinstance(d["id"], int)
    assert isinstance(d["title"], str)
    assert isinstance(d["details"], str)
    assert d["priority"] in {"low", "normal", "urgent"}
    assert d["due"] == now.date().isoformat()
    # created_at and updated_at must be ISO‑8601 strings
    for key in ("created_at", "updated_at"):
        iso = d[key]
        # datetime.fromisoformat will raise if format is wrong
        parsed = datetime.fromisoformat(iso)
        assert parsed.tzinfo is not None, f"{key} must be timezone‑aware"


def test_create_ticket_invalid_filed_by_and_extra_key(db):
    """Clause 2 – create_ticket raises ValueError for invalid filed_by or extra keys."""
    # Invalid filed_by
    with pytest.raises(ValueError):
        create_ticket(db, "unknown", {"title": "x"})
    # Extra key
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "x", "extra": 1})


def test_create_ticket_field_validations(db):
    """Clause 3 – field validation for create_ticket."""
    # Title missing
    with pytest.raises(ValueError):
        create_ticket(db, "her", {})
    # Title too long / empty after strip
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": " "})
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "a" * 121})
    # Details too long
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "t", "details": "b" * 1001})
    # Invalid priority
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "t", "priority": "high"})
    # Invalid due format
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "t", "due": "2023-02-30"})  # invalid date
    with pytest.raises(ValueError):
        create_ticket(db, "her", {"title": "t", "due": 123})
    # Ensure nothing was persisted for a failing case
    count = db.query(Ticket).count()
    assert count == 0


def test_create_ticket_successful_creation(db):
    """Clause 4 – successful ticket creation behavior."""
    data = {
        "title": "  My Ticket  ",
        "details": "Some details",
        "priority": "urgent",
        "due": "2099-12-31",
    }
    ticket_dict = create_ticket(db, "her", data)
    # Verify returned dict matches ticket_to_dict output
    ticket = db.get(Ticket, ticket_dict["id"])
    assert ticket is not None
    # Title should be stripped
    assert ticket.title == "My Ticket"
    # Status, assigned_to, filed_by
    assert ticket.status == "open"
    assert ticket.filed_by == "her"
    assert ticket.assigned_to == "him"
    # Timestamps equal and timezone‑aware UTC
    assert ticket.created_at == ticket.updated_at
    assert ticket.created_at.tzinfo == timezone.utc
    # Commit was performed – we can query it again
    db.refresh(ticket)
    # ticket_to_dict representation matches returned dict
    assert ticket_to_dict(ticket) == ticket_dict
    # due stored as date, dict shows ISO string
    assert ticket_dict["due"] == "2099-12-31"
    # priority stored correctly
    assert ticket_dict["priority"] == "urgent"
    # created_at / updated_at ISO format strings
    for key in ("created_at", "updated_at"):
        iso = ticket_dict[key]
        parsed = datetime.fromisoformat(iso)
        assert parsed.tzinfo is not None
        assert parsed == ticket.created_at
    # Ensure only one ticket exists
    assert db.query(Ticket).count() == 1

