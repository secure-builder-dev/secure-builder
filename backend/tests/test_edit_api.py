"""E4: PATCH /api/tickets/{id} (plans/design.md, E4 rules and API)."""
import pytest

from tests.conftest import BAD, HER, HIM, set_times


def _new(client, headers=HER, **body):
    response = client.post("/api/tickets", json={"title": "Task", **body}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _patch(client, tid, body, headers=HER):
    return client.patch(f"/api/tickets/{tid}", json=body, headers=headers)


def _kinds(client, tid):
    return [e["kind"] for e in client.get(f"/api/tickets/{tid}/history", headers=HER).json()["events"]]


def test_patch_without_a_valid_token_answers_401(client):
    tid = _new(client)["id"]
    for headers in ({}, BAD):
        response = _patch(client, tid, {"title": "New"}, headers)
        assert response.status_code == 401
        assert response.json() == {"error": "unauthorized"}


def test_the_filer_edits_every_field(client):
    t = _new(client, headers=HER, title="Paint", details="fence", priority="low", due="2026-11-01")
    response = _patch(client, t["id"], {"title": "  Paint the fence ", "details": "white", "priority": "urgent",
                                        "due": None})
    assert response.status_code == 200
    got = response.json()
    assert (got["title"], got["details"], got["priority"], got["due"]) == ("Paint the fence", "white", "urgent", None)
    assert (got["id"], got["status"], got["filed_by"], got["assigned_to"]) == (t["id"], "open", "her", "him")
    assert got["created_at"] == t["created_at"]
    assert got["updated_at"] >= t["updated_at"]
    assert client.get(f"/api/tickets/{t['id']}", headers=HIM).json() == got


def test_an_edit_changes_only_the_given_fields(client):
    t = _new(client, headers=HER, title="Paint", details="fence", priority="low", due="2026-11-01")
    got = _patch(client, t["id"], {"due": "2026-12-24"}).json()
    assert (got["title"], got["details"], got["priority"], got["due"]) == ("Paint", "fence", "low", "2026-12-24")


def test_an_acknowledged_ticket_can_still_be_edited(client):
    tid = _new(client, headers=HER)["id"]
    client.post(f"/api/tickets/{tid}/status", json={"status": "acknowledged"}, headers=HIM)
    assert _patch(client, tid, {"priority": "urgent"}).status_code == 200


def test_an_edit_adds_an_edited_event(client):
    tid = _new(client, headers=HER)["id"]
    _patch(client, tid, {"title": "Renamed"})
    events = client.get(f"/api/tickets/{tid}/history", headers=HIM).json()["events"]
    assert [(e["actor"], e["kind"], e["from_status"], e["to_status"]) for e in events] == [
        ("her", "filed", None, "open"), ("her", "edited", None, None)]


def test_the_other_user_cannot_edit_the_filers_ticket(client):
    t = _new(client, headers=HER)
    response = _patch(client, t["id"], {"title": "Mine now"}, HIM)
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
    assert client.get(f"/api/tickets/{t['id']}", headers=HER).json() == t
    assert _kinds(client, t["id"]) == ["filed"]


@pytest.mark.parametrize("status", ["in_progress", "done", "closed"])
def test_a_ticket_past_acknowledged_answers_409(client, db, status):
    t = _new(client, headers=HER)
    set_times(db, t["id"], status=status)
    response = _patch(client, t["id"], {"title": "Too late"})
    assert response.status_code == 409
    assert response.json() == {"error": "not editable"}
    assert client.get(f"/api/tickets/{t['id']}", headers=HER).json()["title"] == "Task"
    assert _kinds(client, t["id"]) == ["filed"]


def test_editing_a_missing_ticket_answers_404(client):
    response = _patch(client, 999999, {"title": "Ghost"})
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


def test_a_non_integer_id_answers_400(client):
    response = _patch(client, "abc", {"title": "X"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": "x" * 121}, {"details": "x" * 1001}, {"priority": "high"},
                                  {"due": "2026-02-30"}, {"due": 20261101}, {"status": "done"}, {"assigned_to": "her"},
                                  {"title": "Fine", "extra": 1}, ["title"]])
def test_invalid_edits_answer_400_and_change_nothing(client, body):
    t = _new(client, headers=HER)
    response = _patch(client, t["id"], body)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}
    assert client.get(f"/api/tickets/{t['id']}", headers=HER).json() == t


def test_an_invalid_edit_by_the_other_user_answers_400_first(client):
    tid = _new(client, headers=HER)["id"]
    assert _patch(client, tid, {"priority": "high"}, HIM).status_code == 400


def test_a_refused_edit_by_the_other_user_on_a_closed_ticket_answers_403_first(client, db):
    tid = _new(client, headers=HER)["id"]
    set_times(db, tid, status="closed")
    assert _patch(client, tid, {"title": "X"}, HIM).status_code == 403


def test_malformed_json_edit_answers_400(client):
    tid = _new(client)["id"]
    response = client.patch(f"/api/tickets/{tid}", content="not json", headers={**HER, "Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_errors_never_echo_the_edit(client):
    tid = _new(client)["id"]
    marker = "<script>alert(1)</script>"
    response = _patch(client, tid, {"priority": marker})
    assert response.status_code == 400
    assert marker not in response.text and "Traceback" not in response.text
