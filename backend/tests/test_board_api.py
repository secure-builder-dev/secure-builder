"""GD-2d: GET /api/board."""
from tests.conftest import BAD, HER, HIM


def _new(client, headers, title):
    response = client.post("/api/tickets", json={"title": title}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_get_api_board_without_authorization_header_answers_401(client):
    response = client.get("/api/board")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_get_api_board_with_a_wrong_token_answers_401(client):
    response = client.get("/api/board", headers=BAD)
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_get_api_board_answers_the_household_board(client):
    a = _new(client, HER, "for him")
    b = _new(client, HIM, "for her")
    response = client.get("/api/board", headers=HER)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"todo", "in_progress", "completed"}
    assert [t["id"] for t in body["todo"]] == [a, b]
    assert body["todo"][0]["assigned_to"] == "him" and body["todo"][1]["assigned_to"] == "her"


def test_both_users_get_the_same_board(client):
    _new(client, HER, "one")
    tid = _new(client, HIM, "two")
    for s in ("acknowledged", "in_progress"):
        client.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HER)
    her, him = client.get("/api/board", headers=HER).json(), client.get("/api/board", headers=HIM).json()
    assert her == him
    assert [t["title"] for t in her["in_progress"]] == ["two"]


def test_get_api_board_carries_the_security_headers(client):
    response = client.get("/api/board", headers=HER)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
