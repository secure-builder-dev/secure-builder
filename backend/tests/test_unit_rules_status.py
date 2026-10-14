import pytest
from datetime import datetime, timezone
from app.rules import change_status, ticket_to_dict
from app.models import Ticket


class TestChangeStatusLookupError:
    """Clause 2: raises LookupError when ticket does not exist or user is not a party."""
    
    def test_raises_lookup_error_when_ticket_does_not_exist(self, db):
        """Ticket ID that doesn't exist raises LookupError."""
        with pytest.raises(LookupError):
            change_status(db, 99999, "her", "acknowledged")
    
    def test_raises_lookup_error_when_user_is_not_filer_or_assignee(self, db):
        """User who is neither filer nor assignee raises LookupError."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(LookupError):
            change_status(db, ticket.id, "stranger", "acknowledged")


class TestChangeStatusValueError:
    """Clause 3: raises ValueError for invalid status or invalid move."""
    
    def test_raises_value_error_for_invalid_new_status(self, db):
        """new_status not in allowed list raises ValueError."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "invalid_status")
    
    def test_raises_value_error_for_move_not_in_table(self, db):
        """Move not in the status table raises ValueError."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        # open -> done is not in the table
        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "done")
    
    def test_raises_value_error_for_move_to_same_status(self, db):
        """Move to the same status raises ValueError."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "open")


class TestChangeStatusPermissionError:
    """Clause 4: raises PermissionError when move is valid but user is wrong party."""
    
    def test_raises_permission_error_when_assignee_moves_done_to_closed(self, db):
        """done -> closed requires filer, not assignee."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, "him", "closed")
    
    def test_raises_permission_error_when_filer_moves_open_to_acknowledged(self, db):
        """open -> acknowledged requires assignee, not filer."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, "her", "acknowledged")


class TestChangeStatusSuccessBehavior:
    """Clause 1 and 5: successful moves apply correctly."""
    
    def test_open_to_acknowledged_by_assignee(self, db):
        """open -> acknowledged by assignee succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "him", "acknowledged")
        assert result['status'] == 'acknowledged'
        assert result['id'] == ticket.id
    
    def test_acknowledged_to_in_progress_by_assignee(self, db):
        """acknowledged -> in_progress by assignee succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="acknowledged",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "him", "in_progress")
        assert result['status'] == 'in_progress'
    
    def test_in_progress_to_done_by_assignee(self, db):
        """in_progress -> done by assignee succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "him", "done")
        assert result['status'] == 'done'
    
    def test_done_to_closed_by_filer(self, db):
        """done -> closed by filer succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "her", "closed")
        assert result['status'] == 'closed'
    
    def test_done_to_open_by_filer(self, db):
        """done -> open (reopen) by filer succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "her", "open")
        assert result['status'] == 'open'
    
    def test_closed_to_open_by_filer(self, db):
        """closed -> open (reopen) by filer succeeds."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "her", "open")
        assert result['status'] == 'open'
    
    def test_successful_move_sets_updated_at(self, db):
        """Successful move updates updated_at to current UTC time."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        old_updated = ticket.updated_at
        result = change_status(db, ticket.id, "him", "acknowledged")
        
        # Parse the returned ISO-8601 string
        new_updated = datetime.fromisoformat(result['updated_at'])
        assert new_updated > old_updated
        assert new_updated.tzinfo is not None
    
    def test_successful_move_returns_ticket_to_dict(self, db):
        """Successful move returns ticket_to_dict of the ticket."""
        ticket = Ticket(
            title="Test Title",
            details="Test Details",
            priority="urgent",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = change_status(db, ticket.id, "him", "acknowledged")
        
        assert result['id'] == ticket.id
        assert result['title'] == 'Test Title'
        assert result['details'] == 'Test Details'
        assert result['priority'] == 'urgent'
        assert result['status'] == 'acknowledged'
        assert result['filed_by'] == 'her'
        assert result['assigned_to'] == 'him'
        assert result['due'] is None
        assert 'created_at' in result
        assert 'updated_at' in result
    
    def test_raising_call_changes_nothing(self, db):
        """A raising call does not change the ticket."""
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        old_status = ticket.status
        old_updated = ticket.updated_at
        
        # This should raise PermissionError (filer trying assignee move)
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, "her", "acknowledged")
        
        # Refresh from database to ensure no changes persisted
        db.refresh(ticket)
        assert ticket.status == old_status
        assert ticket.updated_at == old_updated
