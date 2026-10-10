import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine, init_db, Base
from datetime import date, datetime, timedelta, timezone
from app.models import Ticket

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_tokens(monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    return {"her": "Bearer secret_her", "him": "Bearer secret_him"}

def test_get_board_success(client, auth_tokens):
    # Setup some data to verify content
    from app.db import SessionLocal
    with SessionLocal() as session:
        t1 = Ticket(
            title="T1", 
            status="open", 
            filed_by="her", 
            assigned_to="him", 
            created_at=datetime.now(timezone.utc).replace(microsecond=0)
        )
        t2 = Ticket(
            title="T2", 
            status="in_progress", 
            filed_by="him", 
            assigned_to="her", 
            created_at=datetime.now(timezone.utc).replace(microsecond=0)
        )
        session.add_all([t1, t2])
        session.commit()

    res_her = client.get("/api/board", headers={"Authorization": auth_tokens["her"]})
    res_him = client.get("/api/board", headers={"Authorization": auth_tokens["him"]})
    
    assert res_her.status_code == 200
    assert res_him.status_code == 200
    assert res_her.json() == res_him.json()
    assert len(res_her.json()["todo"]) == 1
    assert len(res_her.json()["in_progress"]) == 1

def test_get_board_unauthorized_no_header(client, auth_tokens):
    res = client.get("/api/board")
    assert res.status_code == 401
    assert res.json() == {"error": "unauthorized"}

def test_get_board_unauthorized_wrong_token(client, auth_tokens):
    res = client.get("/api/board", headers={"Authorization": "Bearer wrong_token"})
    assert res.status_code == 401
    assert res.json() == {"error": "unauthorized"}

def test_get_board_completed_filter(client, auth_tokens):
    from app.db import SessionLocal
    today = date.today()
    with SessionLocal() as session:
        # Within 7 days
        t_recent = Ticket(
            title="Recent",
            status="done",
            filed_by="her",
            assigned_to="him",
            updated_at=datetime.now(timezone.utc).replace(day=today.day)
        )
        # Older than 7 days
        t_old = Ticket(
            title="Old",
            status="done",
            filed_by="her",
            assigned_to="him",
            updated_at=datetime.now(timezone.utc) - timedelta(days=8)
        )
        session.add_all([t_recent, t_old])
        session.commit()

    res = client.get("/api/board", headers={"Authorization": auth_tokens["her"]})
    completed = res.json()["completed"]
    assert len(completed) == 1
    assert completed[0]["title"] == "Recent"