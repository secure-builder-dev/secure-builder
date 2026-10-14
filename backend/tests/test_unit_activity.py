from datetime import datetime, timezone
import pytest

from app.models import Comment, TicketEvent, Ticket
from app.db import SessionLocal


class TestCommentToDict:
    """Tests for comment_to_dict function."""
    
    def test_returns_all_columns_as_plain_dict(self, db):
        """comment_to_dict returns every column as a plain dict."""
        from app.activity import comment_to_dict
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        comment = Comment(
            ticket_id=ticket.id,
            author="her",
            body="Test comment",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        )
        db.add(comment)
        db.commit()
        
        result = comment_to_dict(comment)
        
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'ticket_id' in result
        assert 'author' in result
        assert 'body' in result
        assert 'created_at' in result
        assert result['id'] == comment.id
        assert result['ticket_id'] == ticket.id
        assert result['author'] == "her"
        assert result['body'] == "Test comment"
    
    def test_created_at_is_iso8601_string(self, db):
        """created_at is returned as an ISO-8601 string."""
        from app.activity import comment_to_dict
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        comment = Comment(
            ticket_id=ticket.id,
            author="her",
            body="Test",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        )
        db.add(comment)
        db.commit()
        
        result = comment_to_dict(comment)
        
        assert isinstance(result['created_at'], str)
        # ISO-8601 format should contain T separator
        assert 'T' in result['created_at']


class TestEventToDict:
    """Tests for event_to_dict function."""
    
    def test_returns_all_columns_as_plain_dict(self, db):
        """event_to_dict returns every column as a plain dict."""
        from app.activity import event_to_dict
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        event = TicketEvent(
            ticket_id=ticket.id,
            actor="her",
            kind="filed",
            from_status=None,
            to_status="open",
            at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        )
        db.add(event)
        db.commit()
        
        result = event_to_dict(event)
        
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'ticket_id' in result
        assert 'actor' in result
        assert 'kind' in result
        assert 'from_status' in result
        assert 'to_status' in result
        assert 'at' in result
        assert result['id'] == event.id
        assert result['ticket_id'] == ticket.id
        assert result['actor'] == "her"
        assert result['kind'] == "filed"
        assert result['from_status'] is None
        assert result['to_status'] == "open"
    
    def test_at_is_iso8601_string(self, db):
        """at is returned as an ISO-8601 string."""
        from app.activity import event_to_dict
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        event = TicketEvent(
            ticket_id=ticket.id,
            actor="her",
            kind="filed",
            from_status=None,
            to_status="open",
            at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        )
        db.add(event)
        db.commit()
        
        result = event_to_dict(event)
        
        assert isinstance(result['at'], str)
        # ISO-8601 format should contain T separator
        assert 'T' in result['at']


class TestRecordEvent:
    """Tests for record_event function."""
    
    def test_adds_ticket_event_with_utc_time(self, db):
        """record_event adds a TicketEvent with at set to current timezone-aware UTC time."""
        from app.activity import record_event
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        record_event(db, ticket, "her", "filed")
        
        events = db.query(TicketEvent).filter_by(ticket_id=ticket.id).all()
        assert len(events) == 1
        event = events[0]
        assert event.actor == "her"
        assert event.kind == "filed"
        assert event.from_status is None
        assert event.to_status is None
        # Check that at is timezone-aware UTC
        assert event.at.tzinfo is not None
    
    def test_does_not_commit(self, db):
        """record_event does not commit; the event is lost on rollback."""
        from app.activity import record_event
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        record_event(db, ticket, "her", "filed")
        
        # Rollback the session
        db.rollback()
        
        # The event should not be in the database
        events = db.query(TicketEvent).filter_by(ticket_id=ticket.id).all()
        assert len(events) == 0
    
    def test_accepts_optional_from_status_and_to_status(self, db):
        """record_event accepts optional from_status and to_status parameters."""
        from app.activity import record_event
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        record_event(db, ticket, "him", "status", from_status="open", to_status="acknowledged")
        db.commit()
        
        events = db.query(TicketEvent).filter_by(ticket_id=ticket.id).all()
        assert len(events) == 1
        event = events[0]
        assert event.from_status == "open"
        assert event.to_status == "acknowledged"


class TestAddComment:
    """Tests for add_comment function."""
    
    def test_raises_lookup_error_when_ticket_does_not_exist(self, db):
        """add_comment raises LookupError when the ticket does not exist."""
        from app.activity import add_comment
        
        with pytest.raises(LookupError):
            add_comment(db, 99999, "her", "Test comment")
    
    def test_raises_lookup_error_when_user_is_not_filer_or_assignee(self, db):
        """add_comment raises LookupError when user is neither filer nor assignee."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(LookupError):
            add_comment(db, ticket.id, "someone_else", "Test comment")
    
    def test_raises_value_error_when_body_is_not_str(self, db):
        """add_comment raises ValueError when body is not a str."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(ValueError):
            add_comment(db, ticket.id, "her", 12345)
    
    def test_raises_value_error_when_body_is_empty_after_stripping(self, db):
        """add_comment raises ValueError when body is empty after stripping."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(ValueError):
            add_comment(db, ticket.id, "her", "   ")
    
    def test_raises_value_error_when_body_over_500_chars_after_stripping(self, db):
        """add_comment raises ValueError when body is over 500 characters after stripping."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        long_body = "x" * 501
        with pytest.raises(ValueError):
            add_comment(db, ticket.id, "her", long_body)
    
    def test_stores_stripped_body_with_author_and_created_at(self, db):
        """add_comment stores the stripped body with author user and created_at now."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        body_with_spaces = "  Test comment with spaces  "
        result = add_comment(db, ticket.id, "her", body_with_spaces)
        
        assert result['body'] == "Test comment with spaces"
        assert result['author'] == "her"
        assert 'created_at' in result
    
    def test_commits_and_returns_comment_to_dict(self, db):
        """add_comment commits and returns comment_to_dict of the created comment."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = add_comment(db, ticket.id, "her", "Test comment")
        
        # Verify it's committed by querying fresh
        comments = db.query(Comment).filter_by(ticket_id=ticket.id).all()
        assert len(comments) == 1
        
        # Verify return value is a dict with expected keys
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'ticket_id' in result
        assert 'author' in result
        assert 'body' in result
        assert 'created_at' in result
    
    def test_assignee_can_add_comment(self, db):
        """add_comment allows the assignee to add a comment."""
        from app.activity import add_comment
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        result = add_comment(db, ticket.id, "him", "Test comment")
        assert result['author'] == "him"


class TestCommentDoesNotChangeTicket:
    """Tests that adding a comment does not change the ticket."""
    
    def test_ticket_updated_at_unchanged_after_comment(self, db):
        """A comment leaves the ticket itself unchanged, including its updated_at."""
        from app.activity import add_comment
        
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.commit()
        
        original_updated_at = ticket.updated_at
        
        add_comment(db, ticket.id, "her", "Test comment")
        
        # Refresh ticket from database
        db.refresh(ticket)
        assert ticket.updated_at == original_updated_at
    
    def test_ticket_other_fields_unchanged_after_comment(self, db):
        """A comment leaves all ticket fields unchanged."""
        from app.activity import add_comment
        
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            title="Test",
            details="Some details",
            priority="urgent",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.commit()
        
        original_title = ticket.title
        original_details = ticket.details
        original_priority = ticket.priority
        original_status = ticket.status
        
        add_comment(db, ticket.id, "her", "Test comment")
        
        # Refresh ticket from database
        db.refresh(ticket)
        assert ticket.title == original_title
        assert ticket.details == original_details
        assert ticket.priority == original_priority
        assert ticket.status == original_status


class TestListComments:
    """Tests for list_comments function."""
    
    def test_raises_lookup_error_when_ticket_does_not_exist(self, db):
        """list_comments raises LookupError when the ticket does not exist."""
        from app.activity import list_comments
        
        with pytest.raises(LookupError):
            list_comments(db, 99999, "her")
    
    def test_raises_lookup_error_when_user_is_not_filer_or_assignee(self, db):
        """list_comments raises LookupError when user is not a party."""
        from app.activity import list_comments
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(LookupError):
            list_comments(db, ticket.id, "someone_else")
    
    def test_returns_only_ticket_comments(self, db):
        """list_comments returns only that ticket's comments."""
        from app.activity import add_comment, list_comments
        
        ticket1 = Ticket(
            title="Test 1",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        ticket2 = Ticket(
            title="Test 2",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket1)
        db.add(ticket2)
        db.commit()
        
        add_comment(db, ticket1.id, "her", "Comment for ticket 1")
        add_comment(db, ticket2.id, "her", "Comment for ticket 2")
        
        result = list_comments(db, ticket1.id, "her")
        
        assert len(result) == 1
        assert result[0]['ticket_id'] == ticket1.id
    
    def test_returns_comments_oldest_first_by_created_at_then_id(self, db):
        """list_comments returns comments oldest first by created_at then id."""
        from app.activity import add_comment, list_comments
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        # Add first comment
        add_comment(db, ticket.id, "her", "First comment")
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        # Add second comment
        add_comment(db, ticket.id, "him", "Second comment")
        
        result = list_comments(db, ticket.id, "her")
        
        assert len(result) == 2
        # First comment should be first (oldest created_at)
        assert result[0]['body'] == "First comment"
        assert result[1]['body'] == "Second comment"
    
    def test_returns_comments_as_dicts(self, db):
        """list_comments returns comments as dicts."""
        from app.activity import add_comment, list_comments
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        add_comment(db, ticket.id, "her", "Test comment")
        
        result = list_comments(db, ticket.id, "her")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert 'id' in result[0]
        assert 'ticket_id' in result[0]
        assert 'author' in result[0]
        assert 'body' in result[0]
        assert 'created_at' in result[0]


class TestTicketHistory:
    """Tests for ticket_history function."""
    
    def test_raises_lookup_error_when_ticket_does_not_exist(self, db):
        """ticket_history raises LookupError when the ticket does not exist."""
        from app.activity import ticket_history
        
        with pytest.raises(LookupError):
            ticket_history(db, 99999, "her")
    
    def test_raises_lookup_error_when_user_is_not_filer_or_assignee(self, db):
        """ticket_history raises LookupError when user is not a party."""
        from app.activity import ticket_history
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        with pytest.raises(LookupError):
            ticket_history(db, ticket.id, "someone_else")
    
    def test_returns_only_ticket_events(self, db):
        """ticket_history returns only that ticket's events."""
        from app.activity import record_event, ticket_history
        
        ticket1 = Ticket(
            title="Test 1",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        ticket2 = Ticket(
            title="Test 2",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket1)
        db.add(ticket2)
        db.commit()
        
        record_event(db, ticket1, "her", "filed")
        record_event(db, ticket2, "her", "filed")
        db.commit()
        
        result = ticket_history(db, ticket1.id, "her")
        
        assert len(result) == 1
        assert result[0]['ticket_id'] == ticket1.id
    
    def test_returns_events_oldest_first_by_at_then_id(self, db):
        """ticket_history returns events oldest first by at then id."""
        from app.activity import record_event, ticket_history
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        # Add events
        record_event(db, ticket, "her", "filed")
        record_event(db, ticket, "him", "status", from_status="open", to_status="acknowledged")
        db.commit()
        
        result = ticket_history(db, ticket.id, "her")
        
        assert len(result) == 2
        # First event should be first (oldest at)
        assert result[0]['kind'] == "filed"
        assert result[1]['kind'] == "status"
    
    def test_returns_events_as_dicts(self, db):
        """ticket_history returns events as dicts."""
        from app.activity import record_event, ticket_history
        
        ticket = Ticket(
            title="Test",
            details="",
            priority="normal",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(ticket)
        db.commit()
        
        record_event(db, ticket, "her", "filed")
        db.commit()
        
        result = ticket_history(db, ticket.id, "her")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert 'id' in result[0]
        assert 'ticket_id' in result[0]
        assert 'actor' in result[0]
        assert 'kind' in result[0]
        assert 'from_status' in result[0]
        assert 'to_status' in result[0]
        assert 'at' in result[0]