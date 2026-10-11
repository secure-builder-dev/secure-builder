import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

TOKEN_HER = "secret_her"
TOKEN_HIM = "secret_him"

@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    # Set environment variables for tokens
    monkeypatch.setenv("TOKEN_HER", TOKEN_HER)
    monkeypatch.setenv("TOKEN_HIM", TOKEN_HIM)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_get_me_her(client):
    """Clause 1: GET /api/me answers 200 with {'user': 'her'} for TOKEN_HER"""
    response = client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {TOKEN_HER}"}
    )
    assert response.status_code == 200
    assert response.json() == {"user": "her"}

def test_get_me_him(client):
    """Clause 1: GET /api/me answers 200 with {'user': 'him'} for TOKEN_HIM"""
    response = client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {TOKEN_HIM}"}
    )
    assert response.status_code == 200
    assert response.json() == {"user": "him"}

def test_get_me_no_auth(client):
    """Clause 2: GET /api/me without Authorization header answers 401"""
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_get_me_wrong_token(client):
    """Clause 2: GET /api/me with token matching neither user answers 401"""
    response = client.get(
        "/api/me",
        headers={"Authorization": "Bearer wrong_token"}
    )
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}