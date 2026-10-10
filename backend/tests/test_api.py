import pytest
import os
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app.db import Base
from app.main import app

@pytest.fixture(scope="function", autouse=True)
def setup_db(monkeypatch):
    # Clause 12: sets TOKEN_HER and TOKEN_HIM with monkeypatch.setenv
    monkeypatch.setenv("TOKEN_HER", "secret_her")
    monkeypatch.setenv("TOKEN_HIM", "secret_him")
    
    # Clause 12: uses the database in TICKETER_DATABASE_URL
    db_url = os.getenv("TICKETER_DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:55432/ticketer")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def client():
    # Clause 12: uses fastapi.testclient.TestClient
    return TestClient(app)

def test_health_endpoint(client):
    # Clause 7: GET /health answers 200 with {"status": "ok"} and needs no credential
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Gate requirement: assert it never answers 401 or 403
    unittest.TestCase().assertNotIn(response.status_code, (401, 403))
    
    # Also verify with invalid token that it still doesn't refuse
    response_invalid = client.get("/health", headers={"Authorization": "Bearer wrong"})
    unittest.TestCase().assertNotIn(response_invalid.status_code, (401, 403))

def test_auth_missing_header(client):
    # Clause 2: missing header answered 401
    response = client.get("/api/filed")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_invalid_token(client):
    # Clause 2: token matching neither answered 401
    response = client.get("/api/filed", headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_empty_env_var(client, monkeypatch):
    # Clause 2: unset or empty variable is answered 401
    monkeypatch.setenv("TOKEN_HER", "")
    response = client.get("/api/filed", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}

def test_auth_success_her(client):
    # Clause 2: TOKEN_HER identifies 'her'
    response = client.get("/api/filed", headers={"Authorization": "Bearer secret_her"})
    assert response.status_code == 200

def test_create_ticket(client):
    # Clause 3: POST /api/tickets creates a ticket
    headers = {"Authorization": "Bearer secret_her"}
    payload = {"title": "Test Ticket", "details": "Details", "priority": "normal"}
    response = client.post("/api/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Ticket"
    assert data["filed_by"] == "her"
    assert data["assigned_to"] == "him"

def test_change_status_success(client):
    # Clause 4: POST /api/tickets/{id}/status success
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    t = client.post("/api/tickets", json={"title": "T1"}, headers=headers_her).json()
    tid = t["id"]
    
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=headers_him)
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"

def test_change_status_errors(client):
    # Clause 4: 404, 403, 409
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    # 404 Not Found
    response = client.post("/api/tickets/999/status", json={"status": "acknowledged"}, headers=headers_him)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}
    
    t = client.post("/api/tickets", json={"title": "T2"}, headers=headers_her).json()
    tid = t["id"]
    
    # 403 Forbidden
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=headers_her)
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
    
    # 409 Invalid Transition
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "closed"}, headers=headers_him)
    assert response.status_code == 409
    assert response.json() == {"error": "invalid transition"}

def test_other_user_cannot_make_the_assignees_move(client):
    # Gate requirement: record-scoped route refusal
    headers_her = {"Authorization": "Bearer secret_her"}
    headers_him = {"Authorization": "Bearer secret_him"}
    
    # Her files a ticket, Him is assignee
    t = client.post("/api/tickets", json={"title": "T_Scope"}, headers=headers_her).json()
    tid = t["id"]
    
    # Her (filer) tries to acknowledge (assignee move)
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=headers_her)
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
    
    # Verify status is unchanged
    response_check = client.get("/api/filed", headers=headers_her)
    tickets = response_check.json()["tickets"]
    ticket = next(tk for tk in tickets if tk["id"] == tid)
    assert ticket["status"] == "open"

def test_dashboard(client):
    # Clause 5: GET /api/dashboard
    headers = {"Authorization": "Bearer secret_him"}
    response = client.get("/api/dashboard", headers=headers)
    assert response.status_code == 200
    assert "todo" in response.json()

def test_filed(client):
    # Clause 6: GET /api/filed
    headers = {"Authorization": "Bearer secret_her"}
    client.post("/api/tickets", json={"title": "T1"}, headers=headers)
    response = client.get("/api/filed", headers=headers)
    assert response.status_code == 200
    assert "tickets" in response.json()

def test_invalid_request_400(client):
    # Clause 8: malformed JSON, non-object, invalid fields, non-integer id
    headers = {"Authorization": "Bearer secret_her"}
    
    # Non-integer ID
    response = client.post("/api/tickets/abc/status", json={"status": "done"}, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}
    
    # Body not a JSON object
    response = client.post("/api/tickets", content="not json", headers=headers)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}

def test_body_too_large(client):
    # Clause 9: body over 65536 bytes
    headers = {"Authorization": "Bearer secret_her"}
    large_body = "a" * 65537
    response = client.post("/api/tickets", content=large_body, headers=headers)
    assert response.status_code == 413
    assert response.json() == {"error": "too large"}

def test_unknown_path_and_method(client):
    # Clause 10: 404 unknown path, 405 wrong method
    response = client.get("/api/ghost")
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}
    
    response = client.put("/health")
    assert response.status_code == 405
    assert response.json() == {"error": "method not allowed"}

def test_security_headers(client):
    # Clause 11: Security headers
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
