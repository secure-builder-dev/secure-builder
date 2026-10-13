from datetime import date, datetime, timezone, timedelta
import pytest

from app.models import Ticket
from app.rules import dashboard, filed, ticket_to_dict


class TestDashboard:
    """Tests for rules.dashboard function."""

    def test_dashboard_returns_correct_structure(self, db):
        """Clause 1: dashboard returns dict with todo, in_progress, completed keys."""
        today = date(2025, 6, 15)
        result = dashboard(db, "her", today)
        
        assert isinstance(result, dict)
        assert "todo" in result
        assert "in_progress" in result
        assert "completed" in result
        assert isinstance(result["todo"], list)
        assert isinstance(result["in_progress"], list)
        assert isinstance(result["completed"], list)

    def test_dashboard_only_assigned_tickets(self, db):
        """Clause 1: dashboard returns only tickets assigned to user."""
        today = date(2025, 6, 15)
        
        # Create ticket assigned to 'her'
        ticket_her = Ticket(
            title="Her task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        # Create ticket assigned to 'him'
        ticket_him = Ticket(
            title="His task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_her)
        db.add(ticket_him)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        # Only her's ticket should appear
        all_tickets = []
        for category in ["todo", "in_progress", "completed"]:
            all_tickets.extend(result[category])
        
        assert len(all_tickets) == 1
        assert all_tickets[0]["id"] == ticket_her.id

    def test_todo_contains_open_and_acknowledged(self, db):
        """Clause 2: todo holds tickets with status open or acknowledged."""
        today = date(2025, 6, 15)
        
        # Open ticket
        ticket_open = Ticket(
            title="Open task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        # Acknowledged ticket
        ticket_ack = Ticket(
            title="Acknowledged task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="acknowledged",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        # In progress ticket (should NOT be in todo)
        ticket_in_progress = Ticket(
            title="In progress task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_open)
        db.add(ticket_ack)
        db.add(ticket_in_progress)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        todo_ids = {t["id"] for t in result["todo"]}
        assert ticket_open.id in todo_ids
        assert ticket_ack.id in todo_ids
        assert ticket_in_progress.id not in todo_ids

    def test_in_progress_contains_only_in_progress(self, db):
        """Clause 2: in_progress holds tickets with status in_progress."""
        today = date(2025, 6, 15)
        
        # In progress ticket
        ticket_in_progress = Ticket(
            title="In progress task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        # Open ticket (should NOT be in in_progress)
        ticket_open = Ticket(
            title="Open task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_in_progress)
        db.add(ticket_open)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        in_progress_ids = {t["id"] for t in result["in_progress"]}
        assert ticket_in_progress.id in in_progress_ids
        assert ticket_open.id not in in_progress_ids

    def test_group_0_for_urgent_priority(self, db):
        """Clause 2: group is 0 when priority is 'urgent'."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Urgent task",
            details="",
            priority="urgent",
            due=date(2025, 7, 1),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 0

    def test_group_0_for_due_before_today(self, db):
        """Clause 2: group is 0 when due is before today."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Overdue task",
            details="",
            priority="low",
            due=date(2025, 6, 10),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 0

    def test_group_1_for_due_today(self, db):
        """Clause 2: group is 1 when due is today."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Due today task",
            details="",
            priority="low",
            due=date(2025, 6, 15),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 1

    def test_group_1_for_due_within_3_days(self, db):
        """Clause 2: group is 1 when due is within 3 days after today."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Due in 3 days task",
            details="",
            priority="low",
            due=date(2025, 6, 18),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 1

    def test_group_2_for_due_after_3_days(self, db):
        """Clause 2: group is 2 when due is more than 3 days after today."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Due in 4 days task",
            details="",
            priority="low",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 2

    def test_group_2_for_no_due_date(self, db):
        """Clause 2: group is 2 when there is no due date."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="No due date task",
            details="",
            priority="low",
            due=None,
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert result["todo"][0]["group"] == 2

    def test_ordering_by_group_then_due_then_created(self, db):
        """Clause 3: todo and in_progress ordered by group, then due date (none last), then created_at."""
        today = date(2025, 6, 15)
        
        # Group 0: urgent
        ticket_g0_urgent = Ticket(
            title="Urgent",
            details="",
            priority="urgent",
            due=date(2025, 7, 1),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 5, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 5, 10, 0, tzinfo=timezone.utc)
        )
        
        # Group 0: overdue
        ticket_g0_overdue = Ticket(
            title="Overdue",
            details="",
            priority="low",
            due=date(2025, 6, 10),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 3, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 3, 10, 0, tzinfo=timezone.utc)
        )
        
        # Group 1: due today
        ticket_g1_today = Ticket(
            title="Due today",
            details="",
            priority="low",
            due=date(2025, 6, 15),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc)
        )
        
        # Group 1: due in 2 days
        ticket_g1_later = Ticket(
            title="Due in 2 days",
            details="",
            priority="low",
            due=date(2025, 6, 17),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc)
        )
        
        # Group 2: no due date
        ticket_g2_no_due = Ticket(
            title="No due",
            details="",
            priority="low",
            due=None,
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc)
        )
        
        # Group 2: due far
        ticket_g2_far = Ticket(
            title="Due far",
            details="",
            priority="low",
            due=date(2025, 7, 1),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_g0_urgent)
        db.add(ticket_g0_overdue)
        db.add(ticket_g1_today)
        db.add(ticket_g1_later)
        db.add(ticket_g2_no_due)
        db.add(ticket_g2_far)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        todo = result["todo"]
        assert len(todo) == 6
        
        # Group 0 first (overdue before urgent due to due date ordering)
        assert todo[0]["id"] == ticket_g0_overdue.id
        assert todo[1]["id"] == ticket_g0_urgent.id
        
        # Group 1 next (today before later)
        assert todo[2]["id"] == ticket_g1_today.id
        assert todo[3]["id"] == ticket_g1_later.id
        
        # Group 2 last (far date before no due date)
        assert todo[4]["id"] == ticket_g2_far.id
        assert todo[5]["id"] == ticket_g2_no_due.id

    def test_completed_contains_done_and_closed(self, db):
        """Clause 4: completed holds tickets with status done or closed."""
        today = date(2025, 6, 15)
        
        # Done ticket within window
        ticket_done = Ticket(
            title="Done task",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        )
        
        # Closed ticket within window
        ticket_closed = Ticket(
            title="Closed task",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="closed",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 14, 10, 0, tzinfo=timezone.utc)
        )
        
        # Open ticket (should NOT be in completed)
        ticket_open = Ticket(
            title="Open task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_done)
        db.add(ticket_closed)
        db.add(ticket_open)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        completed_ids = {t["id"] for t in result["completed"]}
        assert ticket_done.id in completed_ids
        assert ticket_closed.id in completed_ids
        assert ticket_open.id not in completed_ids

    def test_completed_within_7_day_window(self, db):
        """Clause 4: completed only includes tickets updated within 7 days (today + 6 before)."""
        today = date(2025, 6, 15)
        
        # Updated today
        ticket_today = Ticket(
            title="Updated today",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        )
        
        # Updated 6 days ago (within window)
        ticket_6_days = Ticket(
            title="Updated 6 days ago",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 9, 10, 0, tzinfo=timezone.utc)
        )
        
        # Updated 7 days ago (outside window)
        ticket_7_days = Ticket(
            title="Updated 7 days ago",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 8, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_today)
        db.add(ticket_6_days)
        db.add(ticket_7_days)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        completed_ids = {t["id"] for t in result["completed"]}
        assert ticket_today.id in completed_ids
        assert ticket_6_days.id in completed_ids
        assert ticket_7_days.id not in completed_ids

    def test_completed_ordered_newest_updated_first(self, db):
        """Clause 4: completed ordered by newest updated_at first."""
        today = date(2025, 6, 15)
        
        ticket_newer = Ticket(
            title="Newer",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 14, 10, 0, tzinfo=timezone.utc)
        )
        
        ticket_older = Ticket(
            title="Older",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 10, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_newer)
        db.add(ticket_older)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["completed"]) == 2
        assert result["completed"][0]["id"] == ticket_newer.id
        assert result["completed"][1]["id"] == ticket_older.id

    def test_completed_has_no_group_key(self, db):
        """Clause 4: completed tickets do not have a group key."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Done task",
            details="",
            priority="normal",
            due=date(2025, 6, 10),
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["completed"]) == 1
        assert "group" not in result["completed"][0]

    def test_todo_has_group_key(self, db):
        """Clause 2: todo tickets have a group key."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="Open task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["todo"]) == 1
        assert "group" in result["todo"][0]

    def test_in_progress_has_group_key(self, db):
        """Clause 2: in_progress tickets have a group key."""
        today = date(2025, 6, 15)
        
        ticket = Ticket(
            title="In progress task",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket)
        db.commit()
        
        result = dashboard(db, "her", today)
        
        assert len(result["in_progress"]) == 1
        assert "group" in result["in_progress"][0]

    def test_dashboard_with_no_tickets(self, db):
        """Clause 1: dashboard returns empty lists when no tickets exist."""
        today = date(2025, 6, 15)
        
        result = dashboard(db, "her", today)
        
        assert result["todo"] == []
        assert result["in_progress"] == []
        assert result["completed"] == []


class TestFiled:
    """Tests for rules.filed function."""

    def test_filed_returns_correct_structure(self, db):
        """Clause 5: filed returns a list of ticket_to_dict dicts."""
        result = filed(db, "her")
        
        assert isinstance(result, list)

    def test_filed_returns_all_tickets_user_filed(self, db):
        """Clause 5: filed returns every ticket user filed, whatever its status."""
        # Create tickets filed by 'her' with different statuses
        ticket_open = Ticket(
            title="Open filed",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        ticket_done = Ticket(
            title="Done filed",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc)
        )
        
        ticket_closed = Ticket(
            title="Closed filed",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 3, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 3, 10, 0, tzinfo=timezone.utc)
        )
        
        # Ticket filed by 'him' (should NOT appear)
        ticket_him = Ticket(
            title="His ticket",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_open)
        db.add(ticket_done)
        db.add(ticket_closed)
        db.add(ticket_him)
        db.commit()
        
        result = filed(db, "her")
        
        assert len(result) == 3
        result_ids = {t["id"] for t in result}
        assert ticket_open.id in result_ids
        assert ticket_done.id in result_ids
        assert ticket_closed.id in result_ids
        assert ticket_him.id not in result_ids

    def test_filed_ordered_newest_created_first(self, db):
        """Clause 5: filed ordered by newest created_at first."""
        ticket_newer = Ticket(
            title="Newer",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 5, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 5, 10, 0, tzinfo=timezone.utc)
        )
        
        ticket_older = Ticket(
            title="Older",
            details="",
            priority="normal",
            due=date(2025, 6, 20),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 6, 1, 10, 0, tzinfo=timezone.utc)
        )
        
        db.add(ticket_newer)
        db.add(ticket_older)
        db.commit()
        
        result = filed(db, "her")
        
        assert len(result) == 2
        assert result[0]["id"] == ticket_newer.id
        assert result[1]["id"] == ticket_older.id

    def test_filed_with_no_tickets(self, db):
        """Clause 5: filed returns empty list when user has no tickets."""
        result = filed(db, "her")
        
        assert result == []