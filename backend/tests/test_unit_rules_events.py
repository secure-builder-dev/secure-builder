from datetime import datetime, timezone

import pytest

from app.models import Ticket, TicketEvent
from app.rules import create_ticket, change_status


class TestCreateTicketRecordsEvent:
    """Test that create_ticket records a 'filed' event."""
    
    def test_create_ticket_records_filed_event(self, db):
        """Clause 1: create_ticket records one event of kind 'filed' with actor the filer, from_status None and to_status 'open'."""
        data = {'title': 'Test ticket'}
        result = create_ticket(db, 'her', data)
        
        # Get the ticket ID from the result
        ticket_id = result['id']
        
        # Query for events for this ticket
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).all()
        
        assert len(events) == 1
        event = events[0]
        assert event.kind == 'filed'
        assert event.actor == 'her'
        assert event.from_status is None
        assert event.to_status == 'open'
        assert event.at is not None
    
    def test_create_ticket_event_stored_in_same_commit(self, db):
        """Clause 1: Event is stored in the same commit as the ticket."""
        data = {'title': 'Test ticket'}
        result = create_ticket(db, 'her', data)
        
        # Commit the session to ensure everything is persisted
        db.commit()
        
        # Query again after commit
        ticket_id = result['id']
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).all()
        
        assert len(events) == 1
    
    def test_create_ticket_records_event_for_him(self, db):
        """Clause 1: Works for both users."""
        data = {'title': 'Test ticket from him'}
        result = create_ticket(db, 'him', data)
        
        ticket_id = result['id']
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).all()
        
        assert len(events) == 1
        event = events[0]
        assert event.kind == 'filed'
        assert event.actor == 'him'
        assert event.from_status is None
        assert event.to_status == 'open'


class TestChangeStatusRecordsEvent:
    """Test that change_status records a 'status' event."""
    
    def test_change_status_records_status_event(self, db):
        """Clause 2: change_status records one event of kind 'status' with actor the caller, from_status the old status and to_status the new one."""
        # Create a ticket first
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        # Get the ticket
        ticket = db.query(Ticket).first()
        
        # Change status from open to acknowledged (assignee can do this)
        result = change_status(db, ticket.id, 'him', 'acknowledged')
        
        # Query for events for this ticket
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).all()
        
        # Should have 2 events: one 'filed' from create_ticket, one 'status' from change_status
        assert len(events) == 2
        
        # Find the status event
        status_events = [e for e in events if e.kind == 'status']
        assert len(status_events) == 1
        
        event = status_events[0]
        assert event.kind == 'status'
        assert event.actor == 'him'
        assert event.from_status == 'open'
        assert event.to_status == 'acknowledged'
        assert event.at is not None
    
    def test_change_status_event_stored_in_same_commit(self, db):
        """Clause 2: Event is stored in the same commit as the move."""
        # Create a ticket first
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        # Get the ticket
        ticket = db.query(Ticket).first()
        
        # Change status
        change_status(db, ticket.id, 'him', 'acknowledged')
        
        # Commit and verify
        db.commit()
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).all()
        status_events = [e for e in events if e.kind == 'status']
        
        assert len(status_events) == 1
    
    def test_change_status_records_correct_from_to(self, db):
        """Clause 2: from_status is the old status, to_status is the new one."""
        # Create a ticket (status = 'open')
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        ticket = db.query(app.models.Ticket).first()
        
        # Move open -> acknowledged
        change_status(db, ticket.id, 'him', 'acknowledged')
        
        # Move acknowledged -> in_progress
        change_status(db, ticket.id, 'him', 'in_progress')
        
        events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).all()
        status_events = [e for e in events if e.kind == 'status']
        
        assert len(status_events) == 2
        
        # First status event: open -> acknowledged
        assert status_events[0].from_status == 'open'
        assert status_events[0].to_status == 'acknowledged'
        
        # Second status event: acknowledged -> in_progress
        assert status_events[1].from_status == 'acknowledged'
        assert status_events[1].to_status == 'in_progress'


class TestFailedOperationsRecordNoEvent:
    """Test that failed create_ticket or change_status records no event."""
    
    def test_create_ticket_that_raises_records_no_event(self, db):
        """Clause 3: A create_ticket call that raises records no event."""
        # Invalid filed_by should raise ValueError
        data = {'title': 'Test ticket'}
        
        with pytest.raises(ValueError):
            create_ticket(db, 'invalid_user', data)
        
        # No tickets should exist
        tickets = db.query(Ticket).all()
        assert len(tickets) == 0
        
        # No events should exist
        events = db.query(TicketEvent).all()
        assert len(events) == 0
    
    def test_create_ticket_invalid_title_records_no_event(self, db):
        """Clause 3: create_ticket with invalid title raises and records no event."""
        data = {'title': ''}  # Empty title after stripping
        
        with pytest.raises(ValueError):
            create_ticket(db, 'her', data)
        
        tickets = db.query(Ticket).all()
        assert len(tickets) == 0
        
        events = db.query(TicketEvent).all()
        assert len(events) == 0
    
    def test_change_status_that_raises_records_no_event(self, db):
        """Clause 3: A change_status call that raises records no event."""
        # Create a ticket first
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        ticket = db.query(Ticket).first()
        initial_event_count = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).count()
        
        # Invalid status should raise ValueError
        with pytest.raises(ValueError):
            change_status(db, ticket.id, HIM, 'invalid_status')
        
        # Event count should not have changed
        final_event_count = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).count()
        assert initial_event_count == final_event_count
    
    def test_change_status_permission_error_records_no_event(self, db):
        """Clause 3: change_status with PermissionError records no event."""
        # Create a ticket (her files it, him is assignee)
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        ticket = db.query(Ticket).first()
        initial_event_count = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).count()
        
        # Her (filer) cannot move open -> acknowledged (only assignee can)
        with pytest.raises(PermissionError):
            change_status(db, ticket.id, 'her', 'acknowledged')
        
        # Event count should not have changed
        final_event_count = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket.id).count()
        assert initial_event_count == final_event_count
    
    def test_change_status_lookup_error_records_no_event(self, db):
        """Clause 3: change_status with LookupError records no event."""
        # Create a ticket first
        data = {'title': 'Test ticket'}
        create_ticket(db, 'her', data)
        
        initial_event_count = db.query(TicketEvent).count()
        
        # Non-existent ticket should raise LookupError
        with pytest.raises(LookupError):
            change_status(db, 99999, 'him', 'acknowledged')
        
        # Event count should not have changed
        final_event_count = db.query(TicketEvent).count()
        assert initial_event_count == final_event_count
    
    def test_earlier_behavior_unchanged_success(self, db):
        """Clause 3: Every earlier behaviour of create_ticket and change_status is unchanged."""
        # Test that create_ticket still returns the ticket dict
        data = {'title': 'Test', 'priority': 'urgent'}
        result = create_ticket(db, 'her', data)
        
        assert result['title'] == 'Test'
        assert result['priority'] == 'urgent'
        assert result['status'] == 'open'
        assert result['filed_by'] == 'her'
        assert result['assigned_to'] == 'him'
    
    def test_earlier_behavior_unchanged_change_status_returns_ticket(self, db):
        """Clause 3: change_status still returns the updated ticket dict."""
        data = {'title': 'Test'}
        create_ticket(db, 'her', data)
        
        ticket = db.query(Ticket).first()
        result = change_status(db, ticket.id, 'him', 'acknowledged')
        
        assert result['id'] == ticket.id
        assert result['status'] == 'acknowledged'



