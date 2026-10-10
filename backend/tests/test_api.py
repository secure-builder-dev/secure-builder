import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, init_db
from sqlalchemy import text

@pytest.fixture(scope="function", autouse=True)
def db_setup():
    init_db()
    yield
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tickets"))
        conn.commit()

@pytest.fixture
def client():
    return TestClient(app)

def test_app_initialization(client):
    # Clause 1: FastAPI app exists and calls init_db at startup
    response = client.get("/health")
    assert response.status_code == 200

def test_auth_missing_header(client, monkeypatch):
    # Clause 2: missing header answered 401
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/filed")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_invalid_token(client, monkeypatch):
    # Clause 2: token matching neither answered 401
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/filed", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_empty_env_var(client, monkeypatch):
    # Clause 2: unset or empty variable answered 401
    monkeypatch.setenv("TOKEN_HER", "")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    response = client.get("/api/filed", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_create_ticket_success(client, monkeypatch):
    # Clause 3: POST /api/tickets creates a ticket and answers 201
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    payload = {"title": "Test Ticket", "priority": "normal"}
    response = client.post("/api/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Ticket"
    assert data["filed_by"] == "her"
    assert data["assigned_to"] == "him"

def test_update_status_success(client, monkeypatch):
    # Clause 4: POST /api/tickets/{id}/status answers 200
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    res = client.post("/api/tickets", json={"title": "T1"}, headers=headers_her)
    tid = res.json()["id"]
    
    res = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=headers_him)
    assert res.status_code == 200
    assert res.json()["status"] == "acknowledged"

def test_update_status_not_found(client, monkeypatch):
    # Clause 4: 404 on LookupError
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.post("/api/tickets/999/status", json={"status": "open"}, headers=headers)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}

def test_update_status_forbidden(client, monkeypatch):
    # Clause 4: 403 on PermissionError
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers_her = {"Authorization": "Bearer secret_her"}
    
    res = client.post("/api/tickets", json={"title": "T1"}, headers=headers_her)
    tid = res.json()["id"]
    
    res = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=headers_her)
    assert res.status_code == 403
    assert res.json() == {"error": "forbidden"}

def test_update_status_invalid_transition(client, monkeypatch):
    # Clause 4: 409 on ValueError
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    res = client.post("/api/tickets", json={"title": "T1"}, headers=headers_her)
    tid = res.json()["id"]
    
    res = client.post(f"/api/tickets/{tid}/status", json={"status": "done"}, headers=headers_him)
    assert res.status_code == 409
    assert res.json() == {"error": "invalid transition"}

def test_dashboard_endpoint(client, monkeypatch):
    # Clause 5: GET /api/dashboard answers 200
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.get("/api/dashboard", headers=headers)
    assert response.status_code == 200
    assert "todo" in response.json()

def test_filed_endpoint(client, monkeypatch):
    # Clause 6: GET /api/filed answers 200 with {"tickets": ...}
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.get("/api/filed", headers=headers)
    assert response.status_code == 200
    assert "tickets" in response.json()

def test_health_endpoint(client):
    # Clause 7: GET /health answers 200 with {"status": "ok"}
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_malformed_json(client, monkeypatch):
    # Clause 8: malformed JSON answered 400
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her", "Content-Type": "application/json"}
    response = client.post("/api/tickets", content="{invalid: json}", headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

def test_invalid_body_type(client, monkeypatch):
    # Clause 8: body that is not a JSON object answered 400
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.post("/api/tickets", json=["not an object"], headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

def test_non_integer_id(client, monkeypatch):
    # Clause 8: non-integer id answered 400
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.post("/api/tickets/abc/status", json={"status": "open"}, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

def test_body_too_large(client, monkeypatch):
    # Clause 9: body over 65536 bytes answered 413
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    large_body = "a" * 65537
    response = client.post("/api/tickets", content=large_body, headers=headers)
    assert response.status_code == 413
    assert response.json() == {"error": "too large"}

def test_unknown_path(client):
    # Clause 10: unknown path answers 404
    response = client.get("/api/ghost")
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}

def test_wrong_method(client):
    # Clause 10: wrong method answers 405
    response = client.post("/health")
    assert response.status_code == 405

def test_security_headers(client, monkeypatch):
    # Clause 11: security headers on every response
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    headers = {"Authorization": "Bearer secret_her"}
    response = client.get("/api/filed", headers=headers)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
