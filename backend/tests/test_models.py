"""GD-1a: the database module and the Ticket model."""
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect

BACKEND = Path(__file__).resolve().parent.parent


def _import_db_with(url):
    env = {k: v for k, v in os.environ.items() if k != "TICKETER_DATABASE_URL"}
    if url is not None:
        env["TICKETER_DATABASE_URL"] = url
    # a fixed command: a fresh interpreter, so the module-level check runs again
    # nosemgrep: dangerous-subprocess-use-audit
    return subprocess.run([sys.executable, "-c", "import app.db"], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=60)


def test_db_raises_runtime_error_when_url_unset():
    r = _import_db_with(None)
    assert r.returncode != 0
    assert "RuntimeError" in r.stderr


def test_db_raises_runtime_error_when_url_empty():
    r = _import_db_with("")
    assert r.returncode != 0
    assert "RuntimeError" in r.stderr


def test_db_exports_engine_base_sessionlocal_init_db():
    from sqlalchemy.orm import DeclarativeBase, sessionmaker
    from app import db
    assert issubclass(db.Base, DeclarativeBase)
    assert isinstance(db.SessionLocal, sessionmaker)
    assert str(db.engine.url).startswith("postgresql")
    assert callable(db.init_db)


def test_init_db_creates_the_tickets_table():
    from app.db import Base, engine, init_db
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)
    init_db()
    try:
        assert "tickets" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        Base.metadata.drop_all(engine)


def test_ticket_model_columns():
    from app.models import Ticket
    assert Ticket.__tablename__ == "tickets"
    cols = Ticket.__table__.columns
    assert set(cols.keys()) == {"id", "title", "details", "priority", "due", "status", "filed_by", "assigned_to",
                                "created_at", "updated_at"}
    assert cols["id"].primary_key
    assert cols["created_at"].type.timezone is True
    assert cols["updated_at"].type.timezone is True
    assert cols["due"].type.python_type is dt.date


def test_ticket_round_trips_through_the_database(db):
    from app.models import Ticket
    now = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.timezone.utc)
    t = Ticket(title="Fix the sink", details="", priority="normal", due=dt.date(2026, 10, 5), status="open",
               filed_by="her", assigned_to="him", created_at=now, updated_at=now)
    db.add(t)
    db.commit()
    got = db.get(Ticket, t.id)
    assert isinstance(got.id, int)
    assert got.title == "Fix the sink"
    assert got.due == dt.date(2026, 10, 5)
    assert got.created_at == now
