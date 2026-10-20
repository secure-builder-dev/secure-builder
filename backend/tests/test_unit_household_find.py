"""TO-4b: household_board filters (q, priority, assigned_to) and household.summary."""
import datetime as dt

import pytest

from app.household import household_board, summary
from app.rules import create_ticket
from tests.conftest import at, set_times

TODAY = dt.date(2026, 10, 10)


def _make(db, title, filer="her", status="open", created="2026-10-01", updated=None, **fields):
    t = create_ticket(db, filer, {"title": title, **fields})
    set_times(db, t["id"], created=at(created), updated=at(updated or created), status=status)
    return t["id"]


def _titles(board):
    return {col: [t["title"] for t in board[col]] for col in ("todo", "in_progress", "completed")}


def _sample(db):
    _make(db, "Fix the Sink", filer="her", priority="urgent", created="2026-10-01")
    _make(db, "Mow", filer="him", details="front LAWN and back", created="2026-10-02")
    _make(db, "Groceries", filer="her", priority="low", status="in_progress", created="2026-10-03")
    _make(db, "Lawn chairs", filer="him", priority="urgent", status="done", updated="2026-10-09")
    _make(db, "Old lawn job", filer="her", status="closed", updated="2026-09-01")       # outside the window


@pytest.mark.parametrize("empty", [None, ""])
def test_no_filter_is_the_same_board(db, empty):
    _sample(db)
    plain = household_board(db, TODAY)
    assert household_board(db, TODAY, q=empty, priority=empty, assigned_to=empty) == plain
    assert _titles(plain) == {"todo": ["Fix the Sink", "Mow"], "in_progress": ["Groceries"],
                              "completed": ["Lawn chairs"]}


@pytest.mark.parametrize("q", ["lawn", "LAWN", "LaWn"])
def test_q_matches_title_or_details_ignoring_case(db, q):
    _sample(db)
    assert _titles(household_board(db, TODAY, q=q)) == {"todo": ["Mow"], "in_progress": [],
                                                        "completed": ["Lawn chairs"]}


def test_q_is_a_substring_match(db):
    _sample(db)
    assert _titles(household_board(db, TODAY, q="sin"))["todo"] == ["Fix the Sink"]
    assert _titles(household_board(db, TODAY, q="nothing like it")) == {"todo": [], "in_progress": [],
                                                                       "completed": []}


@pytest.mark.parametrize("q,hit", [("50%", "Save 50% now"), ("a_b", "the a_b key")])
def test_q_is_plain_text_not_a_pattern(db, q, hit):
    _make(db, hit)
    _make(db, "Save 500 now", created="2026-10-02")
    _make(db, "the axb key", created="2026-10-03")
    assert _titles(household_board(db, TODAY, q=q))["todo"] == [hit]


def test_priority_filter(db):
    _sample(db)
    assert _titles(household_board(db, TODAY, priority="urgent")) == {"todo": ["Fix the Sink"], "in_progress": [],
                                                                      "completed": ["Lawn chairs"]}
    assert _titles(household_board(db, TODAY, priority="low"))["in_progress"] == ["Groceries"]


def test_assigned_to_filter(db):
    _sample(db)
    for_him = household_board(db, TODAY, assigned_to="him")       # filed by her
    assert _titles(for_him) == {"todo": ["Fix the Sink"], "in_progress": ["Groceries"], "completed": []}
    for_her = household_board(db, TODAY, assigned_to="her")
    assert _titles(for_her) == {"todo": ["Mow"], "in_progress": [], "completed": ["Lawn chairs"]}
    assert all(t["assigned_to"] == "her" for col in for_her.values() for t in col)


def test_filters_combine_and_an_empty_one_is_ignored(db):
    _sample(db)
    assert _titles(household_board(db, TODAY, q="lawn", priority="urgent", assigned_to="her")) == {
        "todo": [], "in_progress": [], "completed": ["Lawn chairs"]}
    assert _titles(household_board(db, TODAY, q="lawn", priority="", assigned_to="him")) == {
        "todo": [], "in_progress": [], "completed": []}
    assert _titles(household_board(db, TODAY, q="", priority="urgent", assigned_to=None))["todo"] == ["Fix the Sink"]


def test_filtered_board_keeps_the_order_and_no_group_key(db):
    _make(db, "job late", created="2026-10-05", priority="urgent", due="2026-10-01")
    _make(db, "job early", created="2026-09-20", filer="him")
    _make(db, "other", created="2026-09-01")
    b = household_board(db, TODAY, q="job")
    assert _titles(b)["todo"] == ["job early", "job late"]
    assert all("group" not in t for t in b["todo"])


def test_summary_counts_open_overdue_and_due_today(db):
    # assigned to him (filed by her)
    _make(db, "overdue", due="2026-10-09")
    _make(db, "overdue ack", status="acknowledged", due="2026-09-01")
    _make(db, "today", status="in_progress", due="2026-10-10")
    _make(db, "soon", due="2026-10-11")
    _make(db, "no due")
    _make(db, "done overdue", status="done", due="2026-10-01")
    _make(db, "closed today", status="closed", due="2026-10-10")
    # assigned to her (filed by him)
    _make(db, "hers", filer="him", due="2026-10-10")
    assert summary(db, "him", TODAY) == {"overdue": 2, "due_today": 1, "open": 5}
    assert summary(db, "her", TODAY) == {"overdue": 0, "due_today": 1, "open": 1}


def test_summary_is_all_zero_without_tickets(db):
    assert summary(db, "her", TODAY) == {"overdue": 0, "due_today": 0, "open": 0}


def test_summary_uses_the_given_today(db):
    _make(db, "t", due="2026-10-10")
    assert summary(db, "him", dt.date(2026, 10, 11)) == {"overdue": 1, "due_today": 0, "open": 1}
    assert summary(db, "him", dt.date(2026, 10, 9)) == {"overdue": 0, "due_today": 0, "open": 1}
