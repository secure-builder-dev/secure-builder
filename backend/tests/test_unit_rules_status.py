import pytest
from datetime import datetime, timezone, timedelta

from app.rules import change_status, ticket_to_dict
from app.models import Ticket


class TestChangeStatusSuccess:
    """Clause 1: successful status moves per the design table."""

    def test_open_to_acknowledged_by_assignee(self, db):
        t = Ticket(
            title="Buy milk",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "him", "acknowledged")

        assert result["status"] == "acknowledged"
        assert result["id"] == t.id
        # updated_at should be close to now (within 2 seconds)
        now = datetime.now(timezone.utc)
        assert abs((result["updated_at"][:19] if isinstance(result["updated_at"], str) else result["updated_at"]).replace(tzinfo=timezone.utc) - now).total_seconds() < 2

    def test_acknowledged_to_in_progress_by_assignee(self, db):
        t = Ticket(
            title="Walk dog",
            details="",
            priority="normal",
            due=None,
            status="acknowledged",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "him", "in_progress")

        assert result["status"] == "in_progress"

    def test_in_progress_to_done_by_assignee(self, db):
        t = Ticket(
            title="Fix leak",
            details="",
            priority="urgent",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "him", "done")

        assert result["status"] == "done"

    def test_done_to_closed_by_filer(self, db):
        t = Ticket(
            title="Pay bill",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "her", "closed")

        assert result["status"] == "closed"

    def test_done_to_open_by_filer(self, db):
        t = Ticket(
            title="Renew sub",
            details="",
            priority="normal",
            due=None,
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "her", "open")

        assert result["status"] == "open"

    def test_closed_to_open_by_filer(self, db):
        t = Ticket(
            title="Call mom",
            details="",
            priority="low",
            due=None,
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "her", "open")

        assert result["status"] == "open"

    def test_returns_ticket_to_dict(self, db):
        t = Ticket(
            title="Test ticket",
            details="Some details",
            priority="urgent",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        result = change_status(db, t.id, "him", "acknowledged")

        assert "id" in result
        assert "title" in result
        assert "details" in result
        assert "priority" in result
        assert "status" in result
        assert "filed_by" in result
        assert "assigned_to" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert result["title"] == t.title
        assert result["details"] == t.details
        assert result["priority"] == t.priority
        assert result["filed_by"] == t.filed_by
        assert result["assigned_to"] == t.assigned_to


class TestChangeStatusLookupError:
    """Clause 2: LookupError when ticket missing or user not a party."""

    def test_ticket_not_found(self, db):
        with pytest.raises(LookupError):
            change_status(db, 99999, "her", "acknowledged")

    def test_user_is_neither_filer_nor_assignee(self, db):
        t = Ticket(
            title="Buy bread",
            details="",
            priority="normal",
            due=None,
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        with pytest.raises(LookupError):
            change_status(db, t.id, "them", "acknowledged")

    def test_lookup_error_checked_before_value_error(self, db):
        """LookupError is raised before checking new_status validity."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        # Invalid user should raise LookupError, not ValueError for invalid status
        with pytest.raises(LookupError):
            change_status(db, t.id, "them", "invalid_status")

    def test_lookup_error_checked_before_permission_error(self, db):
        """LookupError is raised before checking permission."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        # Invalid user should raise LookupError, not PermissionError
        with pytest.raises(LookupError):
            change_status(db, t.id, "them", "acknowledged")


class TestChangeStatusValueError:
    """Clause 3: ValueError for invalid status or invalid move."""

    def test_invalid_new_status(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(ValueError):
            change_status(db, t.id, "him", "invalid_status")

    def test_move_not_in_table(self, db):
        """open to done is not in the table."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(ValueError):
            change_status(db, t.id, "him", "done")

    def test_move_to_same_status(self, db):
        """A move to the same status is not allowed."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(ValueError):
            change_status(db, t.id, "him", "open")

    def test_value_error_after_lookup_check(self, db):
        """ValueError is raised only after LookupError check passes."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        # Valid user, invalid move -> ValueError
        with pytest.raises(ValueError):
            change_status(db, t.id, "him", "closed")


class TestChangeStatusPermissionError:
    """Clause 4: PermissionError when move is valid but user is wrong party."""

    def test_open_to_acknowledged_by_filer(self, db):
        """Only assignee can move open to acknowledged."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "her", "acknowledged")

    def test_acknowledged_to_in_progress_by_filer(self, db):
        """Only assignee can move acknowledged to in_progress."""
        t = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="acknowledged",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "her", "in_progress")

    def test_in_progress_to_done_by_filer(self, db):
        """Only assignee can move in_progress to done."""
        t = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "her", "done")

    def test_done_to_closed_by_assignee(self, db):
        """Only filer can move done to closed."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "him", "closed")

    def test_done_to_open_by_assignee(self, db):
        """Only filer can move done to open."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "him", "open")

    def test_closed_to_open_by_assignee(self, db):
        """Only filer can move closed to open."""
        t = Ticket(
            title="Test",
            details="",
            priority="normal",
            due=None,
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()

        with pytest.raises(PermissionError):
            change_status(db, t.id, "him", "open")

    def test_permission_error_after_value_error_check(self, db):
        """PermissionError is raised only after ValueError check passes."""
        t = Ticket(
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
        db.add(t)
        db.commit()

        # Valid move, wrong user -> PermissionError (not ValueError)
        with pytest.raises(PermissionError):
            change_status(db, t.id, "her", "acknowledged")


class TestChangeStatusSideEffects:
    """Clause 5: successful move sets status and updated_at, commits, returns dict; raising call changes nothing."""

    def test_successful_move_sets_status(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        old_status = t.status
        change_status(db, t.id, "him", "acknowledged")

        # Refresh from DB to verify commit
        db.refresh(t)
        assert t.status == "acknowledged"
        assert t.status != old_status

    def test_successful_move_sets_updated_at(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        old_updated_at = t.updated_at
        change_status(db, t.id, "him", "acknowledged")

        # Refresh from DB to verify commit
        db.refresh(t)
        assert t.updated_at >= old_updated_at

    def test_successful_move_commits(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        change_status(db, t.id, "him", "acknowledged")

        # Create a new session to verify the commit persisted
        from app.db import SessionLocal
        with SessionLocal() as new_db:
            ticket = new_db.get(Ticket, t.id)
            assert ticket is not None
            assert ticket.status == "acknowledged"

    def test_raising_call_changes_nothing_lookup_error(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        old_status = t.status
        old_updated_at = t.updated_at

        with pytest.raises(LookupError):
            change_status(db, 99999, "her", "acknowledged")

        # Refresh to verify no changes
        db.refresh(t)
        assert t.status == old_status
        assert t.updated_at == old_updated_at

    def test_raising_call_changes_nothing_value_error(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        old_status = t.status
        old_updated_at = t.updated_at

        with pytest.raises(ValueError):
            change_status(db, t.id, "him", "invalid")

        # Refresh to verify no changes
        db.refresh(t)
        assert t.status == old_status
        assert t.updated_at == old_updated_at

    def test_raising_call_changes_nothing_permission_error(self, db):
        t = Ticket(
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
        db.add(t)
        db.commit()

        old_status = t.status
        old_updated_at = t.updated_at

        with pytest.raises(PermissionError):
            change_status(db, t.id, "her", "acknowledged")

        # Refresh to verify no changes
        db.refresh(t)
        assert t.status == old_status
        assert t.updated_at == old_updated_at
