import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.db import Base, SessionLocal, init_db, engine
from app.main import app

@pytest.fixture(scope="function", autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    init_db()
    yield
    with SessionLocal() as session:
        session.execute(text("DROP TABLE IF EXISTS tickets"))
        session.commit()

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    """Clause 7: GET /health answers 200 with {"status": "ok"} and needs no credential"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_auth_missing_header(client):
    """Clause 2: missing header answered 401"""
    response = client.get("/api/filed")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_invalid_token(client):
    """Clause 2: token matching neither answered 401"""
    response = client.get("/api/filed", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_success_her(client):
    """Clause 2: TOKEN_HER identifies 'her'"""
    # We check this indirectly via /api/filed which should return 200
    response = client.get("/api/filed", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 200

def test_create_ticket(client):
    """Clause 3: POST /api/tickets creates a ticket and answers 201"""
    payload = {"title": "Test Ticket", "details": "Details", "priority": "normal", "due": "2026-12-31"}
    response = client.post("/api/tickets", json=payload, headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Ticket"
    assert data["filed_by"] == "her"
    assert data["assigned_to"] == "him"

def test_change_status_success(client):
    """Clause 4: POST /api/tickets/{id}/status answers 200 on success"""
    # Create ticket first
    res = client.post("/api/tickets", json={"title": "T"}, headers={"Authorization": "Bearer secret_her"})
    tid = res.json()["id"]
    
    # Move open -> acknowledged (by him)
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers={"Authorization": "Bearer secret_him"})
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"

def test_change_status_errors(client):
    """Clause 4: 404 on LookupError, 403 on PermissionError, 409 on ValueError"""
    # 404 Not Found
    response = client.post("/api/tickets/999/status", json={"status": "acknowledged"}, headers={"Authorization": "Bearer secret_him"})
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}

    # 403 Forbidden (her cannot acknowledge)
    res = client.post("/api/tickets", json={"title": "T"}, headers={"Authorization": "Bearer secret_her"})
    tid = res.json()["id"]
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}

    # 409 Invalid Transition
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "closed"}, headers={"Authorization": "Bearer secret_him"})
    assert response.status_code == 409
    assert response.json() == {"error": "invalid transition"}

def test_dashboard(client):
    """Clause 5: GET /api/dashboard answers 200"""
    response = client.get("/api/dashboard", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 200
    assert "todo" in response.json()

def test_filed(client):
    """Clause 6: GET /api/filed answers 200 with {"tickets": ...}"""
    response = client.get("/api/filed", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 200
    assert "tickets" in response.json()

def test_invalid_request_400(client):
    """Clause 8: malformed JSON or invalid fields answer 400"""
    # Non-integer ID
    response = client.post("/api/tickets/abc/status", json={"status": "done"}, headers={"Authorization": "Bearer secret_him"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

    # Body not a JSON object
    response = client.post("/api/tickets", content="not json", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

def test_body_too_large(client):
    """Clause 9: body over 65536 bytes answers 413"""
    large_body = "a" * 65537
    response = client.post("/api/tickets", content=large_body, headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 413
    assert response.json() == {"error": "too large"}

def test_unknown_path_and_method(client):
    """Clause 10: unknown path 404, wrong method 405"""
    response = client.get("/api/ghost", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}

    response = client.put("/health")
    assert response.status_code == 405

def test_security_headers(client):
    """Clause 11: security headers on every response"""
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
