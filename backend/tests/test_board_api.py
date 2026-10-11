import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app.db import Base
from app.main import app

@pytest.fixture(scope="function", autouse=True)
def setup_database(monkeypatch):
    db_url = os.environ.get("TICKETER_DATABASE_URL")
    if not db_url:
        pytest.fail("TICKETER_DATABASE_URL not set")
    
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    
    yield
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    return TestClient(app)

def test_get_board_success(client):
    # Both users should see the same board
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    resp_her = client.get("/api/board", headers=headers_her)
    resp_him = client.get("/api/board", headers=headers_him)
    
    assert resp_her.status_code == 200
    assert resp_him.status_code == 200
    assert resp_her.json() == resp_him.json()
    assert "todo" in resp_her.json()
    assert "in_progress" in resp_her.json()
    assert "completed" in resp_her.json()

def test_get_board_unauthorized_no_header(client):
    resp = client.get("/api/board")
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}

def test_get_board_unauthorized_wrong_token(client):
    headers = {"Authorization": "Bearer wrong_token"}
    resp = client.get("/api/board", headers=headers)
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}
