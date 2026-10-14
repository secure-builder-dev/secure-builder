"""GD-1f: POST /api/tickets and POST /api/tickets/{id}/status, request validation and the body limit."""
import pytest

from tests.conftest import BAD, HER, HIM


def _new(client, headers=HER, **body):
    response = client.post("/api/tickets", json={"title": "Task", **body}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_post_api_tickets_without_authorization_header_answers_401(client):
    response = client.post("/api/tickets", json={"title": "T"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}
    response = client.post("/api/tickets", json={"title": "T"}, headers=BAD)
    assert response.status_code == 401


def test_post_api_tickets_status_without_authorization_header_answers_401(client):
    tid = _new(client)["id"]
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=BAD)
    assert response.status_code == 401


def test_post_api_tickets_creates_a_ticket_filed_by_the_caller(client):
    response = client.post("/api/tickets", json={"title": "Fix sink", "details": "drips", "priority": "urgent",
                                                 "due": "2026-10-20"}, headers=HIM)
    assert response.status_code == 201
    t = response.json()
    assert t["title"] == "Fix sink" and t["details"] == "drips" and t["priority"] == "urgent"
    assert t["due"] == "2026-10-20" and t["status"] == "open"
    assert t["filed_by"] == "him" and t["assigned_to"] == "her"
    assert [x["id"] for x in client.get("/api/filed", headers=HIM).json()["tickets"]] == [t["id"]]


def test_post_api_tickets_accepts_null_due_and_defaults(client):
    t = _new(client, title="Minimal", due=None)
    assert t["due"] is None and t["priority"] == "normal" and t["details"] == ""


def test_status_move_answers_200_with_the_ticket(client):
    tid = _new(client)["id"]
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=HIM)
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    assert response.json()["id"] == tid


def test_status_move_for_a_missing_ticket_answers_404(client):
    response = client.post("/api/tickets/999999/status", json={"status": "acknowledged"}, headers=HIM)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


def test_other_user_cannot_make_the_assignees_move(client):
    tid = _new(client, headers=HER)["id"]
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=HER)
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
    assert client.get("/api/filed", headers=HER).json()["tickets"][0]["status"] == "open"


def test_other_user_cannot_close_the_filers_ticket(client):
    tid = _new(client, headers=HER)["id"]
    for s in ("acknowledged", "in_progress", "done"):
        assert client.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HIM).status_code == 200
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "closed"}, headers=HIM)
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
    response = client.post(f"/api/tickets/{tid}/status", json={"status": "closed"}, headers=HER)
    assert response.status_code == 200


def test_a_move_not_in_the_table_answers_409(client):
    tid = _new(client)["id"]
    for s in ("done", "closed", "open", "ghost"):
        response = client.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HIM)
        assert response.status_code == 409, s
        assert response.json() == {"error": "invalid transition"}


@pytest.mark.parametrize("body", [
    {"details": "no title"},
    {"title": ""},
    {"title": "x" * 121},
    {"title": "T", "priority": "high"},
    {"title": "T", "due": "2026-02-30"},
    {"title": "T", "extra": 1},
    {"title": "T", "assigned_to": "her"},
])
def test_invalid_ticket_fields_answer_400(client, body):
    response = client.post("/api/tickets", json=body, headers=HER)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


@pytest.mark.parametrize("raw", ["not json", "{\"title\": ", "[1, 2]", "\"a string\"", "42", "null"])
def test_malformed_json_or_a_non_object_body_answers_400(client, raw):
    response = client.post("/api/tickets", content=raw, headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


@pytest.mark.parametrize("body", [{}, {"status": 5}, {"state": "done"}, ["done"], {"status": "acknowledged", "x": 1}])
def test_invalid_status_body_answers_400(client, body):
    tid = _new(client)["id"]
    response = client.post(f"/api/tickets/{tid}/status", json=body, headers=HIM)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_a_non_integer_id_answers_400(client):
    response = client.post("/api/tickets/abc/status", json={"status": "acknowledged"}, headers=HIM)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_errors_never_echo_the_input(client):
    marker = "<script>alert(1)</script>"
    for response in (
        client.post("/api/tickets", json={"title": "T", "priority": marker}, headers=HER),
        client.post("/api/tickets", content=marker, headers={**HER, "Content-Type": "application/json"}),
        client.post(f"/api/tickets/{marker}/status", json={"status": "done"}, headers=HER),
    ):
        assert response.status_code in (400, 404)
        assert marker not in response.text
        assert "Traceback" not in response.text


def test_a_body_over_65536_bytes_answers_413(client):
    big = '{"title": "' + "x" * 70000 + '"}'
    response = client.post("/api/tickets", content=big, headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json() == {"error": "too large"}


def test_a_body_of_exactly_65536_bytes_is_read(client):
    body = '{"title": "T", "details": "' + "x" * (65536 - 29) + '"}'
    assert len(body.encode()) == 65536
    response = client.post("/api/tickets", content=body, headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 400          # read and validated: details is far over 1000 characters
    assert response.json() == {"error": "invalid request"}


def test_new_and_moved_tickets_show_on_the_boards(client):
    tid = _new(client, headers=HER, title="Paint fence")["id"]
    assert [t["id"] for t in client.get("/api/dashboard", headers=HIM).json()["todo"]] == [tid]
    client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=HIM)
    client.post(f"/api/tickets/{tid}/status", json={"status": "in_progress"}, headers=HIM)
    board = client.get("/api/dashboard", headers=HIM).json()
    assert board["todo"] == [] and [t["id"] for t in board["in_progress"]] == [tid]
