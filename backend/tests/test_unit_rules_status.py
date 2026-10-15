import pytest
from datetime import datetime, timezone
from app.rules import change_status, ticket_to_dict
from app.models import Ticket


class TestChangeStatus:
    """Unit tests for change_status function."""

    def test_valid_moves_by_assignee(self, db):
        """Clause 1: Valid moves by assignee work."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        # Test open -> acknowledged
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "him", "acknowledged")
        assert result["status"] == "acknowledged"
        assert result["updated_at"] != before

        # Test acknowledged -> in_progress
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "him", "in_progress")
        assert result["status"] == "in_progress"
        assert result["updated_at"] != before

        # Test in_progress -> done
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "him", "done")
        assert result["status"] == "done"
        assert result["updated_at"] != before

    def test_valid_moves_by_filer(self, db):
        """Clause 1: Valid moves by filer work."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        # Test done -> closed
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "her", "closed")
        assert result["status"] == "closed"
        assert result["updated_at"] != before

        # Test done -> open (reopen)
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "her", "open")
        assert result["status"] == "open"
        assert result["updated_at"] != before

        # Test closed -> open (reopen)
        before = ticket.updated_at.isoformat()
        result = change_status(db, ticket.id, "her", "open")
        assert result["status"] == "open"
        assert result["updated_at"] != before

    def test_lookup_error_when_ticket_missing(self, db):
        """Clause 2: LookupError when ticket does not exist."""
        with pytest.raises(LookupError):
            change_status(db, 99999, "her", "acknowledged")

    def test_lookup_error_when_user_not_party(self, db):
        """Clause 2: LookupError when user is neither filer nor assignee."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        # Test with a third user (not her or him)
        with pytest.raises(LookupError):
            change_status(db, ticket.id, "other", "acknowledged")

    def test_value_error_when_new_status_invalid(self, db):
        """Clause 3: ValueError when new_status is not valid."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "invalid_status")

    def test_value_error_when_move_not_in_table(self, db):
        """Clause 3: ValueError when move is not in the status table."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        # Test move to same status
        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "open")

        # Test invalid move (e.g., open -> done)
        with pytest.raises(ValueError):
            change_status(db, ticket.id, "him", "done")

    def test_permission_error_when_wrong_party(self, db):
        """Clause 4: PermissionError when user is not the party for the move."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        # Test filer trying to move to acknowledged (assignee's move)
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, "her", "acknowledged")

        # Test assignee trying to move to closed (filer's move)
        ticket.status = "done"
        db.commit()
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, "him", "closed")

    def test_successful_move_updates_ticket(self, db):
        """Clause 5: Successful move updates status and updated_at."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        old_updated_at = ticket.updated_at
        result = change_status(db, ticket.id, "him", "acknowledged")

        # Verify the ticket was updated
        updated_ticket = db.query(Ticket).filter(Ticket.id == ticket.id).first()
        assert updated_ticket.status == "acknowledged"
        assert updated_ticket.updated_at > old_updated_at

        # Verify the returned dict matches
        assert result == ticket_to_dict(updated_ticket)

    def test_failed_move_changes_nothing(self, db):
        """Clause 5: Failed move changes nothing."""
        # Create a ticket
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.commit()

        old_status = ticket.status
        old_updated_at = ticket.updated_at

        # Try an invalid move
        try:
            change_status(db, ticket.id, "him", "done")
        except ValueError:
            pass

        # Verify nothing changed
        updated_ticket = db.query(Ticket).filter(Ticket.id == ticket.id).first()
        assert updated_ticket.status == old_status
        assert updated_ticket.updated_at == old_updated_at
