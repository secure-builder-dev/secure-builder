import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import Ticket, Base
from datetime import datetime, timezone, date

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    # The test command sets TICKETER_DATABASE_URL
    init_db()
    yield
    db = SessionLocal()
    Base.metadata.drop_all(bind=db.get_bind())
    db.close()

@pytest.fixture
def client():
    return TestClient(app)

def test_get_board_success(client, monkeypatch):
    # Setup tokens
    monkeypatch.setenv("TOKEN_HER", "token_her")
    monkeypatch.setenv("TOKEN_HIM", "token_him")
    
    db = SessionLocal()
    # Create a ticket for both to see
    t = Ticket(
        title="Test Ticket",
        filed_by="her",
        assigned_to="him",
        status="open",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(t)
    db.commit()
    db.close()

    # Both users should see the same board
    resp_her = client.get("/api/board", headers={"Authorization": "Bearer token_her"})
    resp_him = client.get("/api/board", headers={"Authorization": "Bearer token_him"})

    assert resp_her.status_code == 200
    assert resp_him.status_code == 200
    assert resp_her.json() == resp_him.json()
    assert len(resp_her.json()["todo"]) == 1

def test_get_board_unauthorized_no_header(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "token_her")
    monkeypatch.setenv("TOKEN_HIM", "token_him")
    
    resp = client.get("/api/board")
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}

def test_get_board_unauthorized_wrong_token(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "token_her")
    monkeypatch.setenv("TOKEN_HIM", "token_him")
    
    resp = client.get("/api/board", headers={"Authorization": "Bearer wrong_token"})
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}