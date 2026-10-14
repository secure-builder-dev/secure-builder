from datetime import date, datetime, timezone
import pytest

from app.models import Ticket, TicketEvent
from app.rules import edit_ticket, NotEditable, ticket_to_dict, create_ticket
from tests.conftest import HER, HIM


class TestNotEditableException:
    """Test clause 2: rules.NotEditable is a subclass of Exception and of neither ValueError nor PermissionError."""
    
    def test_not_editable_is_subclass_of_exception(self):
        assert issubclass(NotEditable, Exception)
    
    def test_not_editable_is_not_subclass_of_value_error(self):
        assert not issubclass(NotEditable, ValueError)
    
    def test_not_editable_is_not_subclass_of_permission_error(self):
        assert not issubclass(NotEditable, PermissionError)


class TestEditTicketLookupError:
    """Test clause 1: LookupError when ticket does not exist or user is not a party."""
    
    def test_raises_lookup_error_when_ticket_does_not_exist(self, db):
        with pytest.raises(LookupError):
            edit_ticket(db, 99999, 'her', {'title': 'New title'})
    
    def test_raises_lookup_error_when_user_is_not_a_party(self, db):
        # Create a ticket filed by 'her' and assigned to 'him'
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # A third party user (not 'her' or 'him') should get LookupError
        with pytest.raises(LookupError):
            edit_ticket(db, ticket_id, 'stranger', {'title': 'New title'})


class TestEditTicketValueError:
    """Test clause 1: ValueError when data is not a dict, is empty, holds invalid keys, or holds invalid values."""
    
    def test_raises_value_error_when_data_is_not_a_dict(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', "not a dict")
    
    def test_raises_value_error_when_data_is_empty(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {})
    
    def test_raises_value_error_when_data_has_invalid_key(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'invalid_key': 'value'})
    
    def test_raises_value_error_when_title_is_invalid(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Title too long after stripping
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'title': 'x' * 121})
    
    def test_raises_value_error_when_details_is_invalid(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Details too long
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'details': 'x' * 1001})
    
    def test_raises_value_error_when_priority_is_invalid(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'priority': 'invalid'})
    
    def test_raises_value_error_when_due_is_invalid(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'due': 'invalid-date'})


class TestEditTicketPermissionError:
    """Test clause 1: PermissionError when user is not the filer."""
    
    def test_raises_permission_error_when_user_is_not_the_filer(self, db):
        # Create a ticket filed by 'her' and assigned to 'him'
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # 'him' is the assignee but not the filer, should get PermissionError
        with pytest.raises(PermissionError):
            edit_ticket(db, ticket_id, 'him', {'title': 'New title'})


class TestEditTicketNotEditable:
    """Test clause 1: rules.NotEditable when status is not open or acknowledged."""
    
    def test_raises_not_editable_when_status_is_in_progress(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Change status to in_progress
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        change_status(db, ticket_id, 'him', 'in_progress')
        
        with pytest.raises(NotEditable):
            edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
    
    def test_raises_not_editable_when_status_is_done(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Change status to done
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        change_status(db, ticket_id, 'him', 'in_progress')
        change_status(db, ticket_id, 'him', 'done')
        
        with pytest.raises(NotEditable):
            edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
    
    def test_raises_not_editable_when_status_is_closed(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Change status to closed
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        change_status(db, ticket_id, 'him', 'in_progress')
        change_status(db, ticket_id, 'him', 'done')
        change_status(db, ticket_id, 'her', 'closed')
        
        with pytest.raises(NotEditable):
            edit_ticket(db, ticket_id, 'her', {'title': 'New title'})


class TestEditTicketSuccess:
    """Test clause 3: successful edit changes fields, sets updated_at, records event, commits, returns ticket_to_dict."""
    
    def test_successful_edit_changes_only_given_fields(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Original title', 'details': 'Original details', 'priority': 'normal'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {'title': 'New Title  '})
        
        # Title should be stripped
        assert result['title'] == 'New Title'
        # Other fields should remain unchanged
        assert result['details'] == 'Original details'
        assert result['priority'] == 'normal'
    
    def test_successful_edit_sets_updated_at(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        original_updated_at = ticket['updated_at']
        
        # Small delay to ensure updated_at changes
        import time
        time.sleep(0.01)
        
        result = edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        
        # updated_at should be different (later)
        assert result['updated_at'] > original_updated_at
    
    def test_successful_edit_records_edited_event(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        
        # Check that an event was recorded
        stmt = db.execute(
            db.query(TicketEvent).filter_by(ticket_id=ticket_id)
        ).scalars().all()
        
        events = list(stmt)
        assert len(events) >= 2  # filed event + edited event
        
        # Find the edited event
        edited_events = [e for e in events if e.kind == 'edited']
        assert len(edited_events) == 1
        
        edited_event = edited_events[0]
        assert edited_event.actor == 'her'
        assert edited_event.from_status is None
        assert edited_event.to_status is None
    
    def test_successful_edit_returns_ticket_to_dict(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        
        # Check that result has all expected keys
        assert 'id' in result
        assert 'title' in result
        assert 'details' in result
        assert 'priority' in result
        assert 'due' in result
        assert 'status' in result
        assert 'filed_by' in result
        assert 'assigned_to' in result
        assert 'created_at' in result
        assert 'updated_at' in result
        
        assert result['title'] == 'New title'
    
    def test_successful_edit_allows_editing_details(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {'details': 'New details'})
        assert result['details'] == 'New details'
    
    def test_successful_edit_allows_editing_priority(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {'priority': 'urgent'})
        assert result['priority'] == 'urgent'
    
    def test_successful_edit_allows_editing_due(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {'due': '2026-12-31'})
        assert result['due'] == '2026-12-31'
    
    def test_successful_edit_allows_editing_multiple_fields(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        result = edit_ticket(db, ticket_id, 'her', {
            'title': 'New title',
            'details': 'New details',
            'priority': 'urgent',
            'due': '2026-12-31'
        })
        
        assert result['title'] == 'New title'
        assert result['details'] == 'New details'
        assert result['priority'] == 'urgent'
        assert result['due'] == '2026-12-31'
    
    def test_successful_edit_works_when_status_is_acknowledged(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Change status to acknowledged
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        
        result = edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        assert result['title'] == 'New title'


class TestEditTicketFailedChangesNothing:
    """Test clause 4: a failed edit changes nothing and records nothing."""
    
    def test_failed_edit_due_to_lookup_error_changes_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Original title'})
        ticket_id = ticket['id']
        original_updated_at = ticket['updated_at']
        
        # Try to edit with non-existent ticket
        with pytest.raises(LookupError):
            edit_ticket(db, 99999, 'her', {'title': 'New title'})
        
        # Original ticket should be unchanged
        refreshed = db.get(Ticket, ticket_id)
        assert refreshed.title == 'Original title'
        assert refreshed.updated_at == original_updated_at
    
    def test_failed_edit_due_to_value_error_changes_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Original title'})
        ticket_id = ticket['id']
        original_updated_at = ticket['updated_at']
        
        # Try to edit with invalid data
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'invalid_key': 'value'})
        
        # Original ticket should be unchanged
        refreshed = db.get(Ticket, ticket_id)
        assert refreshed.title == 'Original title'
        assert refreshed.updated_at == original_updated_at
    
    def test_failed_edit_due_to_permission_error_changes_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Original title'})
        ticket_id = ticket['id']
        original_updated_at = ticket['updated_at']
        
        # Try to edit as assignee (not filer)
        with pytest.raises(PermissionError):
            edit_ticket(db, ticket_id, 'him', {'title': 'New title'})
        
        # Original ticket should be unchanged
        refreshed = db.get(Ticket, ticket_id)
        assert refreshed.title == 'Original title'
        assert refreshed.updated_at == original_updated_at
    
    def test_failed_edit_due_to_not_editable_changes_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Original title'})
        ticket_id = ticket['id']
        original_updated_at = ticket['updated_at']
        
        # Change status to in_progress
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        change_status(db, ticket_id, 'him', 'in_progress')
        
        # Try to edit when not editable
        with pytest.raises(NotEditable):
            edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        
        # Original ticket should be unchanged
        refreshed = db.get(Ticket, ticket_id)
        assert refreshed.title == 'Original title'
        assert refreshed.updated_at == original_updated_at
    
    def test_failed_edit_records_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Count events before failed edit
        events_before = list(db.query(TicketEvent).filter_by(ticket_id=ticket_id).all())
        
        # Try to edit with invalid data
        with pytest.raises(ValueError):
            edit_ticket(db, ticket_id, 'her', {'invalid_key': 'value'})
        
        # Count events after failed edit
        events_after = list(db.query(TicketEvent).filter_by(ticket_id=ticket_id).all())
        
        # No new events should be recorded
        assert len(events_after) == len(events_before)
    
    def test_failed_edit_due_to_not_editable_records_nothing(self, db):
        ticket = create_ticket(db, 'her', {'title': 'Test ticket'})
        ticket_id = ticket['id']
        
        # Change status to in_progress
        from app.rules import change_status
        change_status(db, ticket_id, 'him', 'acknowledged')
        change_status(db, ticket_id, 'him', 'in_progress')
        
        # Count events before failed edit
        events_before = list(db.query(TicketEvent).filter_by(ticket_id=ticket_id).all())
        
        # Try to edit when not editable
        with pytest.raises(NotEditable):
            edit_ticket(db, ticket_id, 'her', {'title': 'New title'})
        
        # Count events after failed edit
        events_after = list(db.query(TicketEvent).filter_by(ticket_id=ticket_id).all())
        
        # No new events should be recorded
        assert len(events_after) == len(events_before)
