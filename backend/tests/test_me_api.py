"""GD-2g: GET /api/me."""
from tests.conftest import BAD, HER, HIM


def test_get_api_me_without_authorization_header_answers_401(client):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_get_api_me_with_a_wrong_token_answers_401(client):
    response = client.get("/api/me", headers=BAD)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_get_api_me_names_her(client):
    response = client.get("/api/me", headers=HER)
    assert response.status_code == 200
    assert response.json() == {"user": "her"}


def test_get_api_me_names_him(client):
    response = client.get("/api/me", headers=HIM)
    assert response.status_code == 200
    assert response.json() == {"user": "him"}


def test_get_api_me_wrong_method_answers_405(client):
    response = client.post("/api/me", json={}, headers=HER)
    assert response.status_code == 405
    assert response.json() == {"error": "method not allowed"}
