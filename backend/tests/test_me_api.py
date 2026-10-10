import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine, Base

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_me_her(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/me", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 200
    assert response.json() == {"user": "her"}

def test_me_him(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/me", headers={"Authorization": "Bearer secret_him"})
    assert response.status_code == 200
    assert response.json() == {"user": "him"}

def test_me_no_auth(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_me_wrong_token(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/me", headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}