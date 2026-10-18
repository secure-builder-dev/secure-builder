import datetime
import pytest
from app import rules
from app.models import Ticket


def _make_ticket(session, filed_by, title, status="open", priority="normal", due=None, created_at=None, updated_at=None):
    data = {"title": title}
    ticket_dict = rules.create_ticket(session, filed_by, data)
    ticket = session.get(Ticket, ticket_dict["id"])
    ticket.priority = priority
    ticket.due = due
    ticket.status = status
    if created_at:
        ticket.created_at = created_at
    if updated_at:
        ticket.updated_at = updated_at
    session.commit()
    return ticket


def test_dashboard_returns_correct_structure_and_assigned_tickets(db):
    # Ticket filed by her, assigned to him
    t1 = _make_ticket(db, "her", "Ticket 1")
    # Ticket filed by him, assigned to her
    t2 = _make_ticket(db, "him", "Ticket 2")
    today = datetime.date.today()
    board = rules.dashboard(db, "her", today)
    assert set(board.keys()) == {"todo", "in_progress", "completed"}
    # Only ticket assigned to her should appear (t2)
    ids = {t["id"] for lst in board.values() for t in lst}
    assert t2.id in ids
    assert t1.id not in ids


def test_dashboard_group_assignment(db):
    today = datetime.date.today()
    # urgent priority, no due -> group 0
    u1 = _make_ticket(db, "him", "Urgent no due", priority="urgent")
    # due yesterday -> group 0
    past = today - datetime.timedelta(days=1)
    g0 = _make_ticket(db, "him", "Past due", due=past)
    # due today -> group 1
    g1_today = _make_ticket(db, "him", "Today due", due=today)
    # due in 2 days -> group 1
    g1_future = _make_ticket(db, "him", "Soon due", due=today + datetime.timedelta(days=2))
    # due in 5 days -> group 2
    g2 = _make_ticket(db, "him", "Later due", due=today + datetime.timedelta(days=5))
    board = rules.dashboard(db, "her", today)
    # All tickets are in todo (open status)
    todo_ids = {t["id"] for t in board["todo"]}
    for t in [u1, g0, g1_today, g1_future, g2]:
        assert t.id in todo_ids
    # Verify groups
    groups = {t["id"]: t["group"] for t in board["todo"]}
    assert groups[u1.id] == 0
    assert groups[g0.id] == 0
    assert groups[g1_today.id] == 1
    assert groups[g1_future.id] == 1
    assert groups[g2.id] == 2


def test_dashboard_ordering_by_group_due_created(db):
    today = datetime.date.today()
    # Create three tickets with same group 1 but different due and created_at
    # Ticket A: due today, created earlier
    created_a = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
    a = _make_ticket(db, "him", "A", due=today, created_at=created_a, updated_at=created_a)
    # Ticket B: due in 2 days, created later
    created_b = datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc)
    b = _make_ticket(db, "him", "B", due=today + datetime.timedelta(days=2), created_at=created_b, updated_at=created_b)
    # Ticket C: no due (treated as last), created earliest
    created_c = datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc)
    c = _make_ticket(db, "him", "C", due=None, created_at=created_c, updated_at=created_c)
    board = rules.dashboard(db, "her", today)
    todo = board["todo"]
    # Expected order: group 0 tickets first (none), then group 1 ordered by due date, then group 2 (none), then tickets without due at end.
    # Within group 1, due today (A) before due in 2 days (B). C has no due, should appear after group 1 tickets.
    expected_order = [a.id, b.id, c.id]
    assert [t["id"] for t in todo] == expected_order


def test_dashboard_completed_filter_and_order(db):
    today = datetime.date.today()
    # Ticket done today
    now = datetime.datetime.combine(today, datetime.time.min, tzinfo=datetime.timezone.utc)
    done_today = _make_ticket(db, "him", "Done today", status="done", updated_at=now)
    # Ticket done 2 days ago
    two_days = today - datetime.timedelta(days=2)
    upd_two = datetime.datetime.combine(two_days, datetime.time.min, tzinfo=datetime.timezone.utc)
    done_two = _make_ticket(db, "him", "Done 2 days", status="done", updated_at=upd_two)
    # Ticket closed 6 days ago
    six_days = today - datetime.timedelta(days=6)
    upd_six = datetime.datetime.combine(six_days, datetime.time.min, tzinfo=datetime.timezone.utc)
    closed_six = _make_ticket(db, "him", "Closed 6", status="closed", updated_at=upd_six)
    # Ticket done 8 days ago (outside window)
    eight_days = today - datetime.timedelta(days=8)
    upd_eight = datetime.datetime.combine(eight_days, datetime.time.min, tzinfo=datetime.timezone.utc)
    done_eight = _make_ticket(db, "him", "Done 8", status="done", updated_at=upd_eight)
    board = rules.dashboard(db, "her", today)
    completed = board["completed"]
    # Should contain only the first three tickets, ordered newest updated_at first
    expected_ids = [closed_six.id, done_two.id, done_today.id]
    assert [t["id"] for t in completed] == expected_ids
    # Ensure no group key present
    for t in completed:
        assert "group" not in t


def test_filed_returns_all_filed_tickets_newest_first(db):
    # Create three tickets filed by her at different times
    t1 = _make_ticket(db, "her", "First", created_at=datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc))
    t2 = _make_ticket(db, "her", "Second", created_at=datetime.datetime(2023, 1, 2, tzinfo=datetime.timezone.utc))
    t3 = _make_ticket(db, "her", "Third", created_at=datetime.datetime(2023, 1, 3, tzinfo=datetime.timezone.utc))
    # Ticket filed by him should not appear
    other = _make_ticket(db, "him", "Other")
    result = rules.filed(db, "her")
    ids = [t["id"] for t in result]
    assert ids == [t3.id, t2.id, t1.id]
    assert other.id not in ids

