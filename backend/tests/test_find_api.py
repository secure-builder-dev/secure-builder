"""E4: the household board's filter and GET /api/summary (plans/design.md, E4 rules and API)."""
import datetime as dt

import pytest

from tests.conftest import BAD, HER, HIM


def _today():
    return dt.datetime.now(dt.timezone.utc).date()


def _new(client, headers=HER, **body):
    response = client.post("/api/tickets", json={"title": "Task", **body}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _titles(board):
    return sorted(t["title"] for col in ("todo", "in_progress", "completed") for t in board[col])


@pytest.fixture
def some(client):
    _new(client, HER, title="Fix the SINK", priority="urgent")                    # for him
    _new(client, HER, title="Paint fence", details="the sink side too")            # for him
    _new(client, HIM, title="Buy milk", priority="low")                            # for her
    _new(client, HIM, title="Call plumber", priority="urgent")                     # for her
    return client


def _board(client, **params):
    response = client.get("/api/board", params=params, headers=HER)
    assert response.status_code == 200, response.text
    return response.json()


def test_no_filter_or_empty_values_give_the_whole_board(some):
    every = ["Buy milk", "Call plumber", "Fix the SINK", "Paint fence"]
    assert _titles(_board(some)) == every
    assert _titles(_board(some, q="", priority="", assigned_to="")) == every


def test_q_matches_title_or_details_ignoring_case(some):
    assert _titles(_board(some, q="sink")) == ["Fix the SINK", "Paint fence"]
    assert _titles(_board(some, q="MILK")) == ["Buy milk"]
    assert _titles(_board(some, q="nothing like it")) == []


def test_priority_and_assigned_to_filters(some):
    assert _titles(_board(some, priority="urgent")) == ["Call plumber", "Fix the SINK"]
    assert _titles(_board(some, assigned_to="her")) == ["Buy milk", "Call plumber"]


def test_filters_combine(some):
    assert _titles(_board(some, priority="urgent", assigned_to="him")) == ["Fix the SINK"]
    assert _titles(_board(some, q="sink", priority="normal")) == ["Paint fence"]


def test_a_filtered_board_keeps_the_columns(some):
    tid = _board(some, q="milk")["todo"][0]["id"]
    for s in ("acknowledged", "in_progress"):
        some.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HER)
    board = _board(some, q="milk")
    assert board["todo"] == [] and [t["title"] for t in board["in_progress"]] == ["Buy milk"] and board["completed"] == []


def test_other_query_parameters_are_ignored(some):
    assert len(_titles(_board(some, sort="title", page="2"))) == 4


@pytest.mark.parametrize("params", [{"q": "x" * 121}, {"priority": "high"}, {"assigned_to": "them"}, {"priority": "URGENT"}])
def test_an_invalid_filter_answers_400(some, params):
    response = some.get("/api/board", params=params, headers=HER)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_a_q_of_exactly_120_characters_is_accepted(some):
    assert _titles(_board(some, q="x" * 120)) == []


def test_the_board_filter_without_a_valid_token_answers_401(client):
    for headers in ({}, BAD):
        response = client.get("/api/board", params={"q": "sink"}, headers=headers)
        assert response.status_code == 401


def test_summary_without_a_valid_token_answers_401(client):
    for headers in ({}, BAD):
        response = client.get("/api/summary", headers=headers)
        assert response.status_code == 401
        assert response.json() == {"error": "unauthorized"}


def test_an_empty_summary(client):
    response = client.get("/api/summary", headers=HER)
    assert response.status_code == 200
    assert response.json() == {"overdue": 0, "due_today": 0, "open": 0}
    assert response.headers["Cache-Control"] == "no-store"


def test_summary_counts_the_callers_unfinished_tickets(client):
    today = _today()
    day = dt.timedelta(days=1)
    _new(client, HIM, title="late", due=(today - day).isoformat())         # for her: overdue
    _new(client, HIM, title="today", due=today.isoformat())                # for her: due today
    _new(client, HIM, title="later", due=(today + 3 * day).isoformat())    # for her: open only
    _new(client, HIM, title="whenever")                                    # for her: open only
    done = _new(client, HIM, title="finished", due=(today - day).isoformat())["id"]
    for s in ("acknowledged", "in_progress", "done"):
        client.post(f"/api/tickets/{done}/status", json={"status": s}, headers=HER)
    _new(client, HER, title="for him", due=(today - day).isoformat())      # for him
    assert client.get("/api/summary", headers=HER).json() == {"overdue": 1, "due_today": 1, "open": 4}
    assert client.get("/api/summary", headers=HIM).json() == {"overdue": 1, "due_today": 0, "open": 1}


def test_in_progress_tickets_still_count(client):
    tid = _new(client, HIM, title="started", due=_today().isoformat())["id"]
    for s in ("acknowledged", "in_progress"):
        client.post(f"/api/tickets/{tid}/status", json={"status": s}, headers=HER)
    assert client.get("/api/summary", headers=HER).json() == {"overdue": 0, "due_today": 1, "open": 1}
