import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, SessionLocal, Base
from sqlalchemy import create_engine

# The database URL is provided by the environment in the test command
DATABASE_URL = os.getenv("TICKETER_DATABASE_URL")
engine = create_engine(DATABASE_URL)

@pytest.fixture(autouse=True)
def setup_database():
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_me_her(client, monkeypatch):
    token = "secret_her_123"
    monkeypatch.setenv("TOKEN_HER", token)
    monkeypatch.setenv("TOKEN_HIM", "secret_him_123")
    
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user": "her"}

def test_me_him(client, monkeypatch):
    token = "secret_him_123"
    monkeypatch.setenv("TOKEN_HER", "secret_her_123")
    monkeypatch.setenv("TOKEN_HIM", token)
    
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user": "him"}

def test_me_no_auth(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her_123")
    monkeypatch.setenv("TOKEN_HIM", "secret_him_123")
    
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_me_wrong_token(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her_123")
    monkeypatch.setenv("TOKEN_HIM", "secret_him_123")
    
    response = client.get("/api/me", headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}