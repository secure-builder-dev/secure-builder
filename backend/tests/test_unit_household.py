import pytest
from datetime import date, timedelta
from app.household import household_board
from app.models import Ticket
from app.rules import ticket_to_dict
from tests.conftest import at, set_times


@pytest.fixture
def today():
    return date(2024, 1, 1)


def test_clause_1(db, today):
    """Clause 1: household_board returns dict with todo, in_progress, completed."""
    # Add tickets for both users
    tickets = [
        Ticket(
            title="Test 1",
            details="Details 1",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-31"),
            updated_at=at("2023-12-31"),
        ),
        Ticket(
            title="Test 2",
            details="Details 2",
            priority="urgent",
            due=date(2024, 1, 2),
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=at("2023-12-30"),
            updated_at=at("2023-12-30"),
        ),
        Ticket(
            title="Test 3",
            details="Details 3",
            priority="low",
            due=date(2024, 1, 3),
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-29"),
            updated_at=at("2024-1-1"),
        ),
    ]
    db.add_all(tickets)
    db.commit()

    result = household_board(db, today)

    # Check structure
    assert "todo" in result
    assert "in_progress" in result
    assert "completed" in result

    # Check all tickets are included
    all_tickets = result["todo"] + result["in_progress"] + result["completed"]
    assert len(all_tickets) == 3

    # Check no 'group' key in any ticket
    for ticket in all_tickets:
        assert "group" not in ticket


def test_clause_2_todo_order(db, today):
    """Clause 2: todo holds open/acknowledged tickets ordered by created_at oldest first."""
    tickets = [
        Ticket(
            title="Oldest",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-28"),
            updated_at=at("2023-12-28"),
        ),
        Ticket(
            title="Middle",
            details="",
            priority="normal",
            due=None,
            status="acknowledged",
            filed_by="him",
            assigned_to="her",
            created_at=at("2023-12-29"),
            updated_at=at("2023-12-29"),
        ),
        Ticket(
            title="Newest",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-30"),
            updated_at=at("2023-12-30"),
        ),
    ]
    db.add_all(tickets)
    db.commit()

    result = household_board(db, today)

    # Check todo contains only open/acknowledged
    assert all(t["status"] in ("open", "acknowledged") for t in result["todo"])

    # Check order
    assert result["todo"][0]["title"] == "Oldest"
    assert result["todo"][1]["title"] == "Middle"
    assert result["todo"][2]["title"] == "Newest"


def test_clause_2_in_progress_order(db, today):
    """Clause 2: in_progress holds in_progress tickets ordered by created_at oldest first."""
    tickets = [
        Ticket(
            title="Oldest",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-28"),
            updated_at=at("2023-12-28"),
        ),
        Ticket(
            title="Middle",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=at("2023-12-29"),
            updated_at=at("2023-12-29"),
        ),
        Ticket(
            title="Newest",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-30"),
            updated_at=at("2023-12-30"),
        ),
    ]
    db.add_all(tickets)
    db.commit()

    result = household_board(db, today)

    # Check in_progress contains only in_progress
    assert all(t["status"] == "in_progress" for t in result["in_progress"])

    # Check order
    assert result["in_progress"][0]["title"] == "Oldest"
    assert result["in_progress"][1]["title"] == "Middle"
    assert result["in_progress"][2]["title"] == "Newest"


def test_clause_3_completed_order(db, today):
    """Clause 3: completed holds done/closed tickets with updated_at in last 7 days, newest first."""
    # Add tickets with updated_at in the last 7 days
    tickets_in_window = [
        Ticket(
            title="Day 1",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-26"),
            updated_at=at("2023-12-26"),
        ),
        Ticket(
            title="Day 3",
            details="",
            priority="normal",
            due=None,
            status="closed",
            filed_by="him",
            assigned_to="her",
            created_at=at("2023-12-28"),
            updated_at=at("2023-12-28"),
        ),
        Ticket(
            title="Today",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-31"),
            updated_at=at("2024-1-1"),
        ),
    ]
    db.add_all(tickets_in_window)
    db.commit()

    # Add tickets outside the window
    tickets_outside_window = [
        Ticket(
            title="Too Old",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=at("2023-12-20"),
            updated_at=at("2023-12-20"),
        ),
        Ticket(
            title="Future",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=at("2024-1-2"),
            updated_at=at("2024-1-2"),
        ),
    ]
    db.add_all(tickets_outside_window)
    db.commit()

    result = household_board(db, today)

    # Check completed contains only done/closed in window
    assert all(t["status"] in ("done", "closed") for t in result["completed"])
    assert all(
        today - timedelta(days=6) <= date.fromisoformat(t["updated_at"][:10]) <= today
        for t in result["completed"]
    )

    # Check order (newest first)
    assert result["completed"][0]["title"] == "Today"
    assert result["completed"][1]["title"] == "Day 3"
    assert result["completed"][2]["title"] == "Day 1"

    # Check tickets outside window are excluded
    assert not any(t["title"] in ("Too Old", "Future") for t in result["completed"])
