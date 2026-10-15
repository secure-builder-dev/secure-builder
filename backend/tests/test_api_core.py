"""GD-1e: the FastAPI app — get_caller, GET /health, GET /api/dashboard, GET /api/filed, errors and headers."""
import datetime as dt
import unittest

import pytest

from tests.conftest import BAD, HER, HIM

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "content-security-policy": "default-src 'none'",
    "cache-control": "no-store",
    "referrer-policy": "no-referrer",
}


def _file(client, headers, **body):
    """File a ticket straight through the rules (POST /api/tickets is GD-1f)."""
    from app.db import SessionLocal
    from app.rules import create_ticket
    who = "her" if headers is HER else "him"
    s = SessionLocal()
    try:
        return create_ticket(s, who, {"title": "T", **body})
    finally:
        s.close()


def test_health_is_public():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        unittest.TestCase().assertNotIn(response.status_code, (401, 403))
        response = c.get("/health", headers=BAD)
        unittest.TestCase().assertNotEqual(response.status_code, 401)
        assert response.json() == {"status": "ok"}


def test_startup_calls_init_db():
    from fastapi.testclient import TestClient
    from sqlalchemy import inspect
    from app.db import Base, engine
    from app.main import app
    Base.metadata.drop_all(engine)
    try:
        with TestClient(app):
            assert "tickets" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        Base.metadata.drop_all(engine)


@pytest.mark.parametrize("path", ["/api/dashboard", "/api/filed"])
def test_api_dashboard_and_api_filed_without_authorization_header_answer_401(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


@pytest.mark.parametrize("path", ["/api/dashboard", "/api/filed"])
@pytest.mark.parametrize("headers", [BAD, {"Authorization": "token-her-123"}, {"Authorization": "Bearer "},
                                     {"Authorization": "Basic token-her-123"}])
def test_api_routes_with_a_wrong_token_answer_401(client, path, headers):
    response = client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_an_empty_token_variable_never_matches(client, monkeypatch):
    monkeypatch.setenv("TOKEN_HIM", "")
    response = client.get("/api/filed", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    assert client.get("/api/filed", headers=HER).status_code == 200


def test_an_unset_token_variable_never_matches(client, monkeypatch):
    monkeypatch.delenv("TOKEN_HER")
    response = client.get("/api/filed", headers=HER)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_get_caller_names_her_and_him(client):
    _file(client, HER, title="from her")
    _file(client, HIM, title="from him")
    assert [t["title"] for t in client.get("/api/filed", headers=HER).json()["tickets"]] == ["from her"]
    assert [t["title"] for t in client.get("/api/filed", headers=HIM).json()["tickets"]] == ["from him"]


def test_get_caller_uses_compare_digest():
    import inspect as pyinspect
    from app import main
    assert callable(main.get_caller)
    assert "compare_digest" in pyinspect.getsource(main)


def test_api_filed_answers_the_callers_filed_tickets(client):
    _file(client, HER, title="one")
    _file(client, HER, title="two")
    response = client.get("/api/filed", headers=HER)
    assert response.status_code == 200
    body = response.json()
    assert list(body) == ["tickets"]
    assert {t["title"] for t in body["tickets"]} == {"one", "two"}
    assert client.get("/api/filed", headers=HIM).json() == {"tickets": []}


def test_api_dashboard_answers_the_callers_board_for_today_utc(client):
    today = dt.datetime.now(dt.timezone.utc).date()
    _file(client, HER, title="due today", due=today.isoformat())
    _file(client, HER, title="overdue", due=(today - dt.timedelta(days=1)).isoformat())
    response = client.get("/api/dashboard", headers=HIM)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"todo", "in_progress", "completed"}
    assert [(t["title"], t["group"]) for t in body["todo"]] == [("overdue", 0), ("due today", 1)]
    assert client.get("/api/dashboard", headers=HER).json() == {"todo": [], "in_progress": [], "completed": []}


def test_unknown_path_answers_404(client):
    response = client.get("/api/ghost", headers=HER)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}
    response = client.get("/nothing-here")
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


def test_wrong_method_answers_405(client):
    response = client.delete("/health")
    assert response.status_code == 405
    assert response.json() == {"error": "method not allowed"}
    response = client.put("/api/filed", headers=HER)
    assert response.status_code == 405
    assert response.json() == {"error": "method not allowed"}


@pytest.mark.parametrize("method,path,headers", [
    ("get", "/health", {}),
    ("get", "/api/filed", HER),
    ("get", "/api/dashboard", {}),
    ("get", "/api/ghost", HER),
    ("delete", "/health", {}),
])
def test_security_headers_on_every_response(client, method, path, headers):
    response = getattr(client, method)(path, headers=headers)
    for k, v in SECURITY_HEADERS.items():
        assert response.headers.get(k) == v, k
