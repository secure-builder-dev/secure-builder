"""E3: a ticket by id, its comments and its history over HTTP (plans/design.md, E3 API and activity rules)."""
import pytest

from tests.conftest import BAD, HER, HIM


def _new(client, headers=HER, **body):
    response = client.post("/api/tickets", json={"title": "Task", **body}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _comment(client, tid, body, headers=HER):
    return client.post(f"/api/tickets/{tid}/comments", json={"body": body}, headers=headers)


@pytest.mark.parametrize("method,suffix", [("GET", ""), ("GET", "/comments"), ("POST", "/comments"), ("GET", "/history")])
def test_ticket_routes_without_a_valid_token_answer_401(client, method, suffix):
    tid = _new(client)["id"]
    for headers in ({}, BAD):
        response = client.request(method, f"/api/tickets/{tid}{suffix}", json={"body": "hi"}, headers=headers)
        assert response.status_code == 401, (method, suffix)
        assert response.json() == {"error": "unauthorized"}


def test_get_a_ticket_by_id(client):
    t = _new(client, title="Fix sink", priority="urgent")
    for headers in (HER, HIM):
        response = client.get(f"/api/tickets/{t['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json() == t


@pytest.mark.parametrize("suffix", ["", "/comments", "/history"])
def test_a_missing_ticket_answers_404(client, suffix):
    response = client.get(f"/api/tickets/999999{suffix}", headers=HER)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


def test_commenting_on_a_missing_ticket_answers_404(client):
    response = _comment(client, 999999, "hello")
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


@pytest.mark.parametrize("suffix", ["", "/comments", "/history"])
def test_a_non_integer_id_answers_400(client, suffix):
    response = client.get(f"/api/tickets/abc{suffix}", headers=HER)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_both_users_comment_and_the_list_is_oldest_first(client):
    tid = _new(client, headers=HER)["id"]
    first = _comment(client, tid, "  Which sink?  ", headers=HIM)
    assert first.status_code == 201
    c = first.json()
    assert c["body"] == "Which sink?" and c["author"] == "him" and c["ticket_id"] == tid
    assert isinstance(c["id"], int) and isinstance(c["created_at"], str)
    assert _comment(client, tid, "The kitchen one", headers=HER).status_code == 201
    response = client.get(f"/api/tickets/{tid}/comments", headers=HER)
    assert response.status_code == 200
    got = response.json()["comments"]
    assert [(x["author"], x["body"]) for x in got] == [("him", "Which sink?"), ("her", "The kitchen one")]
    assert got[0] == c


def test_comments_belong_to_their_own_ticket(client):
    a, b = _new(client)["id"], _new(client)["id"]
    _comment(client, a, "on a")
    assert client.get(f"/api/tickets/{b}/comments", headers=HER).json() == {"comments": []}


def test_a_comment_does_not_change_the_ticket(client):
    t = _new(client)
    _comment(client, t["id"], "just a note")
    assert client.get(f"/api/tickets/{t['id']}", headers=HER).json() == t


def test_a_comment_of_exactly_500_characters_is_stored(client):
    tid = _new(client)["id"]
    response = _comment(client, tid, "x" * 500)
    assert response.status_code == 201
    assert response.json()["body"] == "x" * 500


@pytest.mark.parametrize("body", [{"body": ""}, {"body": "   "}, {"body": "x" * 501}, {"body": 5}, {"body": None}, {},
                                  {"text": "hi"}, {"body": "hi", "author": "him"}, ["hi"]])
def test_an_invalid_comment_answers_400_and_stores_nothing(client, body):
    tid = _new(client)["id"]
    response = client.post(f"/api/tickets/{tid}/comments", json=body, headers=HER)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}
    assert client.get(f"/api/tickets/{tid}/comments", headers=HER).json() == {"comments": []}


def test_malformed_json_comment_answers_400(client):
    tid = _new(client)["id"]
    response = client.post(f"/api/tickets/{tid}/comments", content="{\"body\": ",
                           headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_markup_in_a_comment_is_stored_as_plain_text(client):
    tid = _new(client)["id"]
    marker = "<img src=x onerror=alert(1)>"
    assert _comment(client, tid, marker).json()["body"] == marker
    response = client.get(f"/api/tickets/{tid}/comments", headers=HIM)
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["comments"][0]["body"] == marker


def test_a_comment_body_over_65536_bytes_answers_413(client):
    tid = _new(client)["id"]
    big = '{"body": "' + "x" * 70000 + '"}'
    response = client.post(f"/api/tickets/{tid}/comments", content=big, headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json() == {"error": "too large"}


def test_ticket_routes_send_the_security_headers(client):
    tid = _new(client)["id"]
    for response in (client.get(f"/api/tickets/{tid}", headers=HER), client.get(f"/api/tickets/{tid}/history", headers=HER),
                     _comment(client, tid, "hi"), client.get("/api/tickets/999999/comments", headers=HER)):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Content-Security-Policy"] == "default-src 'none'"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Referrer-Policy"] == "no-referrer"


def _events(client, tid, headers=HER):
    response = client.get(f"/api/tickets/{tid}/history", headers=headers)
    assert response.status_code == 200
    return response.json()["events"]


def test_a_new_ticket_has_one_filed_event(client):
    tid = _new(client, headers=HIM)["id"]
    events = _events(client, tid)
    assert len(events) == 1
    e = events[0]
    assert (e["actor"], e["kind"], e["from_status"], e["to_status"], e["ticket_id"]) == ("him", "filed", None, "open", tid)
    assert isinstance(e["id"], int) and isinstance(e["at"], str)


def test_every_status_move_adds_an_event_in_order(client):
    tid = _new(client, headers=HER)["id"]
    for s in ("acknowledged", "in_progress", "done"):
        assert client.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HIM).status_code == 200
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "open"}, headers=HER).status_code == 200
    got = [(e["actor"], e["kind"], e["from_status"], e["to_status"]) for e in _events(client, tid, HIM)]
    assert got == [("her", "filed", None, "open"),
                   ("him", "status", "open", "acknowledged"),
                   ("him", "status", "acknowledged", "in_progress"),
                   ("him", "status", "in_progress", "done"),
                   ("her", "status", "done", "open")]


def test_a_refused_move_or_a_comment_adds_no_event(client):
    tid = _new(client, headers=HER)["id"]
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=HER).status_code == 403
    assert client.post(f"/api/tickets/{tid}/status", json={"status": "done"}, headers=HIM).status_code == 409
    _comment(client, tid, "a note")
    assert [e["kind"] for e in _events(client, tid)] == ["filed"]


def test_an_invalid_new_ticket_records_no_event(client, db):
    assert client.post("/api/tickets", json={"title": ""}, headers=HER).status_code == 400
    from app.models import TicketEvent
    assert db.query(TicketEvent).count() == 0
