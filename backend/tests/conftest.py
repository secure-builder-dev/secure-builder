"""Shared fixtures (given by the plan; read-only). Imports of app code happen inside the fixtures, so a test file that
does not use a fixture still collects before that code exists.

db      -- a session on the test database (TICKETER_DATABASE_URL); every table is created before the test and dropped
           after it, with the session closed first so the drop never waits on it
client  -- a fastapi TestClient over app.main.app, with TOKEN_HER and TOKEN_HIM set; tables as for db
HER, HIM, BAD -- Authorization headers
"""
import datetime as dt

import pytest

HER = {"Authorization": "Bearer token-her-123"}
HIM = {"Authorization": "Bearer token-him-456"}
BAD = {"Authorization": "Bearer not-a-token"}


@pytest.fixture
def tables():
    from app.db import Base, engine
    import app.models  # noqa: F401  (registers Ticket on Base)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(tables):
    from app.db import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(tables, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "token-her-123")
    monkeypatch.setenv("TOKEN_HIM", "token-him-456")
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def at(day, hour=12):
    """A timezone-aware UTC datetime on the given date (a datetime.date or 'YYYY-MM-DD')."""
    if isinstance(day, str):
        day = dt.date.fromisoformat(day)
    return dt.datetime(day.year, day.month, day.day, hour, tzinfo=dt.timezone.utc)


def set_times(session, ticket_id, created=None, updated=None, status=None):
    """Set created_at / updated_at / status directly on the stored ticket (tests that need a particular time)."""
    from app.models import Ticket
    t = session.get(Ticket, ticket_id)
    if created is not None:
        t.created_at = created
    if updated is not None:
        t.updated_at = updated
    if status is not None:
        t.status = status
    session.commit()
