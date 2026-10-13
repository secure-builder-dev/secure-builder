from datetime import date, datetime, timezone, timedelta
import pytest

from app.models import Ticket
from app.rules import ticket_to_dict


class TestHouseholdBoard:
    """Tests for household_board function."""
    
    def test_household_board_exists(self, db):
        """Clause 1: household_board function exists and returns correct structure."""
        from app.household import household_board
        
        result = household_board(db, date.today())
        
        assert isinstance(result, dict)
        assert set(result.keys()) == {"todo", "in_progress", "completed"}
        assert isinstance(result["todo"], list)
        assert isinstance(result["in_progress"], list)
        assert isinstance(result["completed"], list)
    
    def test_household_board_returns_all_tickets(self, db):
        """Clause 1: built from every ticket of both users."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        # Create tickets for both users
        ticket1 = Ticket(
            title="Ticket 1",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        ticket2 = Ticket(
            title="Ticket 2",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="him",
            assigned_to="her",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket1, ticket2])
        db.commit()
        
        result = household_board(db, today)
        
        # Should have both tickets in todo
        assert len(result["todo"]) == 2
        assert len(result["in_progress"]) == 0
        assert len(result["completed"]) == 0
    
    def test_household_board_no_group_key(self, db):
        """Clause 1: each as rules.ticket_to_dict returns it (no group key)."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket = Ticket(
            title="Test ticket",
            details="",
            priority="urgent",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add(ticket)
        db.commit()
        
        result = household_board(db, today)
        
        # Check that tickets do not have 'group' key
        for ticket_dict in result["todo"]:
            assert "group" not in ticket_dict
    
    def test_household_board_ticket_structure(self, db):
        """Clause 1: each as rules.ticket_to_dict returns it."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket = Ticket(
            title="Test ticket",
            details="Some details",
            priority="urgent",
            due=date(2026, 1, 15),
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add(ticket)
        db.commit()
        
        result = household_board(db, today)
        
        assert len(result["todo"]) == 1
        ticket_dict = result["todo"][0]
        
        # Check all expected keys from ticket_to_dict
        expected_keys = {"id", "title", "details", "priority", "due", "status", "filed_by", "assigned_to", "created_at", "updated_at"}
        assert set(ticket_dict.keys()) == expected_keys
    
    def test_todo_holds_open_and_acknowledged(self, db):
        """Clause 2: todo holds the tickets with status open or acknowledged."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket_open = Ticket(
            title="Open ticket",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        ticket_acknowledged = Ticket(
            title="Acknowledged ticket",
            details="",
            priority="normal",
            due=None,
            status="acknowledged",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        ticket_in_progress = Ticket(
            title="In progress ticket",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket_open, ticket_acknowledged, ticket_in_progress])
        db.commit()
        
        result = household_board(db, today)
        
        # Todo should have open and acknowledged only
        todo_titles = {t["title"] for t in result["todo"]}
        assert "Open ticket" in todo_titles
        assert "Acknowledged ticket" in todo_titles
        assert "In progress ticket" not in todo_titles
    
    def test_in_progress_holds_in_progress_status(self, db):
        """Clause 2: in_progress those with status in_progress."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket_in_progress = Ticket(
            title="In progress ticket",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        ticket_open = Ticket(
            title="Open ticket",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket_in_progress, ticket_open])
        db.commit()
        
        result = household_board(db, today)
        
        # In progress should have only in_progress status
        assert len(result["in_progress"]) == 1
        assert result["in_progress"][0]["title"] == "In progress ticket"
    
    def test_todo_ordered_oldest_created_at_first(self, db):
        """Clause 2: todo ordered oldest created_at first."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket1 = Ticket(
            title="First ticket",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(hours=2),
            updated_at=now
        )
        
        ticket2 = Ticket(
            title="Second ticket",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket1, ticket2])
        db.commit()
        
        result = household_board(db, today)
        
        # First ticket should come first (older created_at)
        assert result["todo"][0]["title"] == "First ticket"
        assert result["todo"][1]["title"] == "Second ticket"
    
    def test_in_progress_ordered_oldest_created_at_first(self, db):
        """Clause 2: in_progress ordered oldest created_at first."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket1 = Ticket(
            title="First in progress",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(hours=2),
            updated_at=now
        )
        
        ticket2 = Ticket(
            title="Second in progress",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket1, ticket2])
        db.commit()
        
        result = household_board(db, today)
        
        # First ticket should come first (older created_at)
        assert result["in_progress"][0]["title"] == "First in progress"
        assert result["in_progress"][1]["title"] == "Second in progress"
    
    def test_completed_holds_done_and_closed(self, db):
        """Clause 3: completed holds the tickets with status done or closed."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket_done = Ticket(
            title="Done ticket",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        ticket_closed = Ticket(
            title="Closed ticket",
            details="",
            priority="normal",
            due=None,
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        ticket_open = Ticket(
            title="Open ticket",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        
        db.add_all([ticket_done, ticket_closed, ticket_open])
        db.commit()
        
        result = household_board(db, today)
        
        # Completed should have done and closed only
        completed_titles = {t["title"] for t in result["completed"]}
        assert "Done ticket" in completed_titles
        assert "Closed ticket" in completed_titles
        assert "Open ticket" not in completed_titles
    
    def test_completed_within_7_day_window(self, db):
        """Clause 3: whose updated_at date (UTC) is today or one of the 6 days before today."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        # Ticket updated today - should be included
        ticket_today = Ticket(
            title="Updated today",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        # Ticket updated 6 days ago - should be included (today + 6 days before = 7 day window)
        ticket_6_days_ago = Ticket(
            title="Updated 6 days ago",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=6)
        )
        
        # Ticket updated 7 days ago - should NOT be included
        ticket_7_days_ago = Ticket(
            title="Updated 7 days ago",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=7)
        )
        
        db.add_all([ticket_today, ticket_6_days_ago, ticket_7_days_ago])
        db.commit()
        
        result = household_board(db, today)
        
        completed_titles = {t["title"] for t in result["completed"]}
        assert "Updated today" in completed_titles
        assert "Updated 6 days ago" in completed_titles
        assert "Updated 7 days ago" not in completed_titles
    
    def test_completed_newest_updated_at_first(self, db):
        """Clause 3: newest updated_at first."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket1 = Ticket(
            title="First completed",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(hours=2)
        )
        
        ticket2 = Ticket(
            title="Second completed",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        db.add_all([ticket1, ticket2])
        db.commit()
        
        result = household_board(db, today)
        
        # Second ticket should come first (newer updated_at)
        assert result["completed"][0]["title"] == "Second completed"
        assert result["completed"][1]["title"] == "First completed"
    
    def test_completed_empty_when_no_recent_tickets(self, db):
        """Clause 3: completed is empty when no tickets updated within window."""
        from app.household import household_board
        
        today = date.today()
        now = datetime.now(timezone.utc)
        
        ticket_old = Ticket(
            title="Old completed",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=10)
        )
        
        db.add(ticket_old)
        db.commit()
        
        result = household_board(db, today)
        
        assert len(result["completed"]) == 0
    
    def test_household_board_empty_when_no_tickets(self, db):
        """All columns empty when no tickets exist."""
        from app.household import household_board
        
        today = date.today()
        result = household_board(db, today)
        
        assert result["todo"] == []
        assert result["in_progress"] == []
        assert result["completed"] == []