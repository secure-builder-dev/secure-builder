from datetime import date, timedelta
from app.models import Ticket
from app.household import household_board, summary
from tests.conftest import at


class TestHouseholdBoardFilters:
    """Tests for household_board filtering: q, priority, assigned_to."""
    
    def test_no_filters_returns_all_tickets(self, db):
        """When no filters are given, all tickets are returned."""
        today = date(2025, 1, 15)
        
        # Create tickets for both users
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="Leaking faucet", priority="urgent",
            due=today, status="in_progress", filed_by="him", assigned_to="her",
            created_at=at(today, "09:00"), updated_at=at(today, "09:00")
        )
        t3 = Ticket(
            title="Walk dog", details="", priority="low",
            due=date(2025, 1, 20), status="done", filed_by="her", assigned_to="him",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        board = household_board(db, today)
        
        # All tickets should be in the board
        assert len(board['todo']) == 1  # t1 (open)
        assert len(board['in_progress']) == 1  # t2 (in_progress)
        assert len(board['completed']) == 1  # t3 (done, within window)
    
    def test_q_filter_matches_title_case_insensitive(self, db):
        """q filter matches title ignoring case."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy MILK", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, q="milk")
        
        assert len(board['todo']) == 1
        assert board['todo'][0]['title'] == "Buy MILK"
    
    def test_q_filter_matches_details_case_insensitive(self, db):
        """q filter matches details ignoring case."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Grocery", details="Buy MILK and eggs", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, q="milk")
        
        assert len(board['todo']) == 1
        assert board['todo'][0]['title'] == "Grocery"
    
    def test_q_filter_matches_title_or_details(self, db):
        """q filter matches if found in title OR details."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Grocery", details="Buy milk and eggs", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Fix sink", details="Leaking faucet", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "12:00"), updated_at=at(today, "12:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        board = household_board(db, today, q="milk")
        
        assert len(board['todo']) == 2
        titles = {t['title'] for t in board['todo']}
        assert titles == {"Buy milk", "Grocery"}
    
    def test_q_filter_empty_string_is_no_filter(self, db):
        """Empty string q is treated as no filter."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, q="")
        
        assert len(board['todo']) == 2
    
    def test_q_filter_none_is_no_filter(self, db):
        """None q is treated as no filter."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, q=None)
        
        assert len(board['todo']) == 2
    
    def test_priority_filter_equals(self, db):
        """priority filter matches exactly."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="urgent",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Walk dog", details="", priority="low",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "12:00"), updated_at=at(today, "12:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        board = household_board(db, today, priority="urgent")
        
        assert len(board['todo']) == 1
        assert board['todo'][0]['priority'] == "urgent"
    
    def test_priority_filter_empty_string_is_no_filter(self, db):
        """Empty string priority is treated as no filter."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="urgent",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, priority="")
        
        assert len(board['todo']) == 2
    
    def test_assigned_to_filter_equals(self, db):
        """assigned_to filter matches exactly."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, assigned_to="her")
        
        assert len(board['todo']) == 1
        assert board['todo'][0]['assigned_to'] == "her"
    
    def test_assigned_to_filter_empty_string_is_no_filter(self, db):
        """Empty string assigned_to is treated as no filter."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        board = household_board(db, today, assigned_to="")
        
        assert len(board['todo']) == 2
    
    def test_all_filters_combined(self, db):
        """All filters combined: q, priority, assigned_to."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="urgent task", priority="urgent",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="urgent plumbing", priority="urgent",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Walk dog", details="urgent walk", priority="normal",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "12:00"), updated_at=at(today, "12:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        # Filter: q="urgent", priority="urgent", assigned_to="him"
        board = household_board(db, today, q="urgent", priority="urgent", assigned_to="him")
        
        assert len(board['todo']) == 1
        assert board['todo'][0]['title'] == "Buy milk"
    
    def test_filters_apply_to_all_columns(self, db):
        """Filters apply to todo, in_progress, and completed columns."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Buy milk", details="", priority="urgent",
            due=None, status="open", filed_by="her", assigned_to="him",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="urgent",
            due=None, status="in_progress", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Walk dog", details="", priority="urgent",
            due=None, status="done", filed_by="her", assigned_to="him",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today, "12:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        board = household_board(db, today, priority="urgent", assigned_to="him")
        
        assert len(board['todo']) == 1
        assert len(board['in_progress']) == 0
        assert len(board['completed']) == 1


class TestSummary:
    """Tests for household.summary function."""
    
    def test_summary_counts_open_tickets(self, db):
        """summary returns correct open count for all non-done/closed tickets."""
        today = date(2025, 1, 15)
        
        # Tickets assigned to 'her' with various statuses
        t1 = Ticket(
            title="Buy milk", details="", priority="normal",
            due=date(2025, 1, 20), status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Fix sink", details="", priority="normal",
            due=date(2025, 1, 16), status="acknowledged", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Walk dog", details="", priority="normal",
            due=date(2025, 1, 17), status="in_progress", filed_by="him", assigned_to="her",
            created_at=at(today, "12:00"), updated_at=at(today, "12:00")
        )
        # These should not be counted (done/closed)
        t4 = Ticket(
            title="Done task", details="", priority="normal",
            due=date(2025, 1, 10), status="done", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=5), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        t5 = Ticket(
            title="Closed task", details="", priority="normal",
            due=date(2025, 1, 10), status="closed", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=6), "10:00"),
            updated_at=at(today - timedelta(days=2), "10:00")
        )
        
        db.add_all([t1, t2, t3, t4, t5])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 3
        assert result['overdue'] == 0
        assert result['due_today'] == 0
    
    def test_summary_counts_overdue(self, db):
        """summary counts tickets due before today as overdue."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Overdue task", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        t2 = Ticket(
            title="Also overdue", details="", priority="normal",
            due=date(2025, 1, 10), status="acknowledged", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=5), "10:00"),
            updated_at=at(today - timedelta(days=3), "10:00")
        )
        t3 = Ticket(
            title="Not overdue", details="", priority="normal",
            due=date(2025, 1, 16), status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 3
        assert result['overdue'] == 2
        assert result['due_today'] == 0
    
    def test_summary_counts_due_today(self, db):
        """summary counts tickets due exactly today as due_today."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Due today", details="", priority="normal",
            due=today, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Also due today", details="", priority="normal",
            due=today, status="in_progress", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        t3 = Ticket(
            title="Not due today", details="", priority="normal",
            due=date(2025, 1, 16), status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "12:00"), updated_at=at(today, "12:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 3
        assert result['overdue'] == 0
        assert result['due_today'] == 2
    
    def test_summary_tickets_without_due_date(self, db):
        """Tickets without due date are counted in open but not overdue or due_today."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="No due date", details="", priority="normal",
            due=None, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t2 = Ticket(
            title="Overdue", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 2
        assert result['overdue'] == 1
        assert result['due_today'] == 0
    
    def test_summary_only_assigned_to_user(self, db):
        """summary only counts tickets assigned to the specified user."""
        today = date(2025, 1, 15)
        
        # Tickets assigned to 'her'
        t1 = Ticket(
            title="For her", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        # Tickets assigned to 'him' (should not be counted)
        t2 = Ticket(
            title="For him", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="her", assigned_to="him",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        
        db.add_all([t1, t2])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 1
        assert result['overdue'] == 1
        assert result['due_today'] == 0
    
    def test_summary_empty_when_no_tickets(self, db):
        """summary returns zeros when user has no tickets."""
        today = date(2025, 1, 15)
        
        # Create a ticket assigned to 'him' only
        t1 = Ticket(
            title="For him", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="her", assigned_to="him",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        
        db.add(t1)
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 0
        assert result['overdue'] == 0
        assert result['due_today'] == 0
    
    def test_summary_overdue_and_due_today_mutually_exclusive(self, db):
        """A ticket cannot be both overdue and due_today."""
        today = date(2025, 1, 15)
        
        t1 = Ticket(
            title="Overdue", details="", priority="normal",
            due=date(2025, 1, 14), status="open", filed_by="him", assigned_to="her",
            created_at=at(today - timedelta(days=1), "10:00"),
            updated_at=at(today - timedelta(days=1), "10:00")
        )
        t2 = Ticket(
            title="Due today", details="", priority="normal",
            due=today, status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "10:00"), updated_at=at(today, "10:00")
        )
        t3 = Ticket(
            title="Future", details="", priority="normal",
            due=date(2025, 1, 16), status="open", filed_by="him", assigned_to="her",
            created_at=at(today, "11:00"), updated_at=at(today, "11:00")
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = summary(db, "her", today)
        
        assert result['open'] == 3
        assert result['overdue'] == 1
        assert result['due_today'] == 1
        # overdue + due_today should not exceed open
        assert result['overdue'] + result['due_today'] <= result['open']