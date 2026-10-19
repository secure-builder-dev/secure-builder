import datetime
import pytest
from app import household, rules
from tests.conftest import HER, HIM, at, set_times


def create_ticket(session, filed_by, title, details="", priority="normal", due=None, status="open", assigned_to=None, created_at=None, updated_at=None):
    # Helper to directly insert a ticket with given fields
    if assigned_to is None:
        assigned_to = HER if filed_by == HIM else HIM
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    ticket = rules.Ticket(
        title=title,
        details=details,
        priority=priority,
        due=due,
        status=status,
        filed_by=filed_by,
        assigned_to=assigned_to,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
    session.add(ticket)
    session.flush()
    return ticket


def test_household_board_filters(db):
    today = datetime.date(2023, 5, 10)
    # Ticket matching q and priority and assigned_to
    t1 = create_ticket(db, HER, "Fix sink", "Details about sink", priority="urgent", due=today, status="open")
    # Ticket not matching q
    t2 = create_ticket(db, HER, "Paint wall", "Details about wall", priority="low", status="open")
    # Ticket matching only priority
    t3 = create_ticket(db, HER, "Buy milk", "", priority="urgent", status="open")
    # Ticket matching only assigned_to (him)
    t4 = create_ticket(db, HER, "Clean garage", "", priority="normal", assigned_to=HIM, status="open")
    db.commit()

    # No filters – all tickets appear
    board = household.household_board(db, today)
    assert len(board["todo"]) == 4

    # Filter by q (case‑insensitive)
    board_q = household.household_board(db, today, q="sink")
    ids_q = {t["id"] for t in board_q["todo"]}
    assert ids_q == {t1.id}

    # Filter by priority
    board_pri = household.household_board(db, today, priority="urgent")
    ids_pri = {t["id"] for t in board_pri["todo"]}
    assert ids_pri == {t1.id, t3.id}

    # Filter by assigned_to
    board_assigned = household.household_board(db, today, assigned_to=HIM)
    ids_assigned = {t["id"] for t in board_assigned["todo"]}
    assert ids_assigned == {t4.id}

    # Combined filters (q and priority)
    board_comb = household.household_board(db, today, q="sink", priority="urgent")
    ids_comb = {t["id"] for t in board_comb["todo"]}
    assert ids_comb == {t1.id}

    # Empty string filters act as no filter
    board_empty = household.household_board(db, today, q="", priority="", assigned_to="")
    assert len(board_empty["todo"]) == 4


def test_household_summary_counts(db):
    today = datetime.date(2023, 5, 10)
    # Open tickets assigned to her
    create_ticket(db, HIM, "Task 1", status="open", due=today - datetime.timedelta(days=1), assigned_to=HER)
    create_ticket(db, HIM, "Task 2", status="open", due=today, assigned_to=HER)
    create_ticket(db, HIM, "Task 3", status="open", due=None, assigned_to=HER)
    # Done ticket should be ignored
    create_ticket(db, HIM, "Task 4", status="done", due=today - datetime.timedelta(days=2), assigned_to=HER)
    # Closed ticket should be ignored
    create_ticket(db, HIM, "Task 5", status="closed", due=today, assigned_to=HER)
    db.commit()

    summary = household.summary(db, HER, today)
    assert summary["open"] == 3
    assert summary["overdue"] == 1  # Task 1
    assert summary["due_today"] == 1  # Task 2

    # Summary for him (no tickets)
    summary_him = household.summary(db, HIM, today)
    assert summary_him == {"overdue": 0, "due_today": 0, "open": 0}

    # Invalid user raises
    with pytest.raises(ValueError):
        household.summary(db, "unknown", today)
