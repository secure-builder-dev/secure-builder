"""GD-2c: household_board — every ticket of both users."""
import datetime as dt

from app.household import household_board
from app.rules import create_ticket, ticket_to_dict
from tests.conftest import at, set_times

TODAY = dt.date(2026, 10, 10)


def _make(db, title, filer="her", status="open", created="2026-10-01", updated=None, **fields):
    t = create_ticket(db, filer, {"title": title, **fields})
    set_times(db, t["id"], created=at(created), updated=at(updated or created), status=status)
    return t["id"]


def _titles(col):
    return [t["title"] for t in col]


def test_empty_board(db):
    assert household_board(db, TODAY) == {"todo": [], "in_progress": [], "completed": []}


def test_holds_the_tickets_of_both_users(db):
    _make(db, "for him", filer="her")
    _make(db, "for her", filer="him", created="2026-10-02")
    b = household_board(db, TODAY)
    assert _titles(b["todo"]) == ["for him", "for her"]
    assert {t["assigned_to"] for t in b["todo"]} == {"her", "him"}


def test_columns_by_status(db):
    _make(db, "o", status="open")
    _make(db, "a", status="acknowledged", created="2026-10-02")
    _make(db, "p", status="in_progress")
    _make(db, "d", status="done", updated="2026-10-09")
    _make(db, "c", status="closed", updated="2026-10-08")
    b = household_board(db, TODAY)
    assert _titles(b["todo"]) == ["o", "a"]
    assert _titles(b["in_progress"]) == ["p"]
    assert _titles(b["completed"]) == ["d", "c"]


def test_todo_and_in_progress_are_oldest_created_first_ignoring_priority_and_due(db):
    _make(db, "new urgent", priority="urgent", due="2026-10-01", created="2026-10-05")
    _make(db, "old", created="2026-09-01", filer="him")
    _make(db, "mid", created="2026-10-02")
    _make(db, "p2", status="in_progress", created="2026-10-04")
    _make(db, "p1", status="in_progress", created="2026-10-03", filer="him")
    b = household_board(db, TODAY)
    assert _titles(b["todo"]) == ["old", "mid", "new urgent"]
    assert _titles(b["in_progress"]) == ["p1", "p2"]


def test_completed_window_and_order(db):
    _make(db, "today", status="done", updated="2026-10-10")
    _make(db, "6 days ago", status="closed", updated="2026-10-04", filer="him")
    _make(db, "7 days ago", status="done", updated="2026-10-03")
    _make(db, "yesterday", status="closed", updated="2026-10-09", filer="him")
    assert _titles(household_board(db, TODAY)["completed"]) == ["today", "yesterday", "6 days ago"]


def test_tickets_are_ticket_to_dict_dicts_without_group(db):
    from app.models import Ticket
    tid = _make(db, "x", due="2026-10-11")
    t = household_board(db, TODAY)["todo"][0]
    assert t == ticket_to_dict(db.get(Ticket, tid))
    assert "group" not in t
