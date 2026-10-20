"""GD-1d: dashboard (the personal board) and filed."""
import datetime as dt

from app.rules import create_ticket, dashboard, filed
from tests.conftest import at, set_times

TODAY = dt.date(2026, 10, 10)


def _make(db, title, filer="her", status="open", created="2026-10-01", updated=None, **fields):
    t = create_ticket(db, filer, {"title": title, **fields})
    set_times(db, t["id"], created=at(created), updated=at(updated or created), status=status)
    return t["id"]


def _titles(col):
    return [t["title"] for t in col]


def test_dashboard_has_three_columns(db):
    assert dashboard(db, "him", TODAY) == {"todo": [], "in_progress": [], "completed": []}


def test_dashboard_holds_only_tickets_assigned_to_the_user(db):
    _make(db, "for him", filer="her")
    _make(db, "for her", filer="him")
    assert _titles(dashboard(db, "him", TODAY)["todo"]) == ["for him"]
    assert _titles(dashboard(db, "her", TODAY)["todo"]) == ["for her"]


def test_columns_by_status(db):
    _make(db, "o", status="open")
    _make(db, "a", status="acknowledged")
    _make(db, "p", status="in_progress")
    _make(db, "d", status="done", updated="2026-10-09")
    _make(db, "c", status="closed", updated="2026-10-08")
    b = dashboard(db, "him", TODAY)
    assert sorted(_titles(b["todo"])) == ["a", "o"]
    assert _titles(b["in_progress"]) == ["p"]
    assert _titles(b["completed"]) == ["d", "c"]


def test_groups(db):
    _make(db, "urgent no due", priority="urgent")
    _make(db, "overdue", due="2026-10-09")
    _make(db, "today", due="2026-10-10")
    _make(db, "in 3 days", due="2026-10-13")
    _make(db, "in 4 days", due="2026-10-14")
    _make(db, "no due")
    groups = {t["title"]: t["group"] for t in dashboard(db, "him", TODAY)["todo"]}
    assert groups == {"urgent no due": 0, "overdue": 0, "today": 1, "in 3 days": 1, "in 4 days": 2, "no due": 2}


def test_urgent_with_a_far_due_date_is_group_0(db):
    _make(db, "u", priority="urgent", due="2026-12-01")
    assert dashboard(db, "him", TODAY)["todo"][0]["group"] == 0


def test_in_progress_tickets_carry_group_too(db):
    _make(db, "p", status="in_progress", due="2026-10-11")
    assert dashboard(db, "him", TODAY)["in_progress"][0]["group"] == 1


def test_todo_order_group_then_due_then_created(db):
    _make(db, "g2 no due old", created="2026-09-01")
    _make(db, "g2 far", due="2026-11-01", created="2026-10-05")
    _make(db, "g1 later", due="2026-10-12", created="2026-09-02")
    _make(db, "g1 sooner", due="2026-10-11", created="2026-10-06")
    _make(db, "g0 b", priority="urgent", due="2026-10-20", created="2026-10-02")
    _make(db, "g0 a", due="2026-10-01", created="2026-10-03")
    _make(db, "g2 no due new", created="2026-10-07")
    _make(db, "g1 same due newer", due="2026-10-12", created="2026-10-04")
    assert _titles(dashboard(db, "him", TODAY)["todo"]) == [
        "g0 a", "g0 b", "g1 sooner", "g1 later", "g1 same due newer", "g2 far", "g2 no due old", "g2 no due new"]


def test_in_progress_is_ordered_like_todo(db):
    _make(db, "late", status="in_progress", created="2026-10-02")
    _make(db, "early", status="in_progress", created="2026-10-01")
    _make(db, "urgent", status="in_progress", priority="urgent", created="2026-10-03")
    assert _titles(dashboard(db, "him", TODAY)["in_progress"]) == ["urgent", "early", "late"]


def test_completed_window_is_the_7_days_ending_today(db):
    _make(db, "today", status="done", updated="2026-10-10")
    _make(db, "6 days ago", status="closed", updated="2026-10-04")
    _make(db, "7 days ago", status="done", updated="2026-10-03")
    _make(db, "tomorrow", status="done", updated="2026-10-11")
    assert _titles(dashboard(db, "him", TODAY)["completed"]) == ["today", "6 days ago"]


def test_completed_is_newest_updated_first_and_has_no_group(db):
    _make(db, "older", status="done", updated="2026-10-05")
    _make(db, "newer", status="closed", updated="2026-10-09")
    col = dashboard(db, "him", TODAY)["completed"]
    assert _titles(col) == ["newer", "older"]
    assert all("group" not in t for t in col)


def test_dashboard_tickets_are_full_dicts(db):
    _make(db, "x", due="2026-10-20")
    t = dashboard(db, "him", TODAY)["todo"][0]
    assert t["due"] == "2026-10-20"
    assert t["filed_by"] == "her" and t["assigned_to"] == "him"
    assert isinstance(t["created_at"], str)


def test_filed_returns_the_users_filed_tickets_newest_first(db):
    _make(db, "h1", filer="her", created="2026-10-01")
    _make(db, "h2", filer="her", created="2026-10-03", status="done")
    _make(db, "m1", filer="him", created="2026-10-02")
    assert _titles(filed(db, "her")) == ["h2", "h1"]
    assert _titles(filed(db, "him")) == ["m1"]


def test_filed_includes_every_status_and_full_dicts(db):
    for s in ("open", "acknowledged", "in_progress", "done", "closed"):
        _make(db, s, filer="him", status=s, updated="2026-01-01")
    got = filed(db, "him")
    assert sorted(t["status"] for t in got) == ["acknowledged", "closed", "done", "in_progress", "open"]
    assert all(t["assigned_to"] == "her" and "group" not in t for t in got)


def test_filed_is_empty_for_a_user_with_none(db):
    assert filed(db, "her") == []
