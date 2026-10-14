from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.models import Ticket
from app import rules


class TestHouseholdBoard:
    """Tests for household.household_board function."""

    def test_household_board_returns_correct_structure(self, db):
        """Clause 1: household_board returns dict with todo, in_progress, completed keys."""
        from app.household import household_board
        
        result = household_board(db, date(2024, 1, 15))
        
        assert isinstance(result, dict)
        assert 'todo' in result
        assert 'in_progress' in result
        assert 'completed' in result
        assert isinstance(result['todo'], list)
        assert isinstance(result['in_progress'], list)
        assert isinstance(result['completed'], list)

    def test_household_board_includes_all_tickets(self, db):
        """Clause 1: household_board includes every ticket of both users."""
        from app.household import household_board
        
        # Create tickets for both users
        ticket1 = rules.create_ticket(db, 'her', {'title': 'Her ticket'})
        ticket2 = rules.create_ticket(db, 'him', {'title': 'His ticket'})
        
        result = household_board(db, date(2024, 1, 15))
        
        all_tickets = result['todo'] + result['in_progress'] + result['completed']
        assert len(all_tickets) == 2
        titles = {t['title'] for t in all_tickets}
        assert 'Her ticket' in titles
        assert 'His ticket' in titles

    def test_household_board_no_group_key(self, db):
        """Clause 1: tickets have no group key (unlike dashboard)."""
        from app.household import household_board
        
        rules.create_ticket(db, 'her', {'title': 'Test ticket'})
        
        result = household_board(db, date(2024, 1, 15))
        
        for ticket in result['todo']:
            assert 'group' not in ticket

    def test_household_board_ticket_to_dict_format(self, db):
        """Clause 1: each ticket is formatted as rules.ticket_to_dict returns it."""
        from app.household import household_board
        
        created = rules.create_ticket(db, 'her', {
            'title': 'Test ticket',
            'details': 'Some details',
            'priority': 'urgent',
            'due': '2024-01-20'
        })
        
        result = household_board(db, date(2024, 1, 15))
        
        ticket_in_result = result['todo'][0]
        
        # Check all expected keys from ticket_to_dict
        assert ticket_in_result['id'] == created['id']
        assert ticket_in_result['title'] == 'Test ticket'
        assert ticket_in_result['details'] == 'Some details'
        assert ticket_in_result['priority'] == 'urgent'
        assert ticket_in_result['status'] == 'open'
        assert ticket_in_result['filed_by'] == 'her'
        assert ticket_in_result['assigned_to'] == 'him'
        assert ticket_in_result['due'] == '2024-01-20'
        assert 'created_at' in ticket_in_result
        assert 'updated_at' in ticket_in_result

    def test_todo_contains_open_and_acknowledged(self, db):
        """Clause 2: todo holds tickets with status open or acknowledged."""
        from app.household import household_board
        
        # Create open ticket
        rules.create_ticket(db, 'her', {'title': 'Open ticket'})
        
        # Create acknowledged ticket
        ack_ticket = rules.create_ticket(db, 'him', {'title': 'Ack ticket'})
        rules.change_status(db, ack_ticket['id'], 'her', 'acknowledged')
        
        result = household_board(db, date(2024, 1, 15))
        
        todo_titles = {t['title'] for t in result['todo']}
        assert 'Open ticket' in todo_titles
        assert 'Ack ticket' in todo_titles
        assert len(result['todo']) == 2

    def test_todo_excludes_other_statuses(self, db):
        """Clause 2: todo excludes tickets not open or acknowledged."""
        from app.household import household_board
        
        # Create in_progress ticket
        ip_ticket = rules.create_ticket(db, 'her', {'title': 'In progress ticket'})
        rules.change_status(db, ip_ticket['id'], 'him', 'acknowledged')
        rules.change_status(db, ip_ticket['id'], 'him', 'in_progress')
        
        # Create done ticket
        done_ticket = rules.create_ticket(db, 'him', {'title': 'Done ticket'})
        rules.change_status(db, done_ticket['id'], 'her', 'acknowledged')
        rules.change_status(db, done_ticket['id'], 'her', 'in_progress')
        rules.change_status(db, done_ticket['id'], 'her', 'done')
        
        result = household_board(db, date(2024, 1, 15))
        
        todo_titles = {t['title'] for t in result['todo']}
        assert 'In progress ticket' not in todo_titles
        assert 'Done ticket' not in todo_titles
        assert len(result['todo']) == 0

    def test_in_progress_contains_only_in_progress(self, db):
        """Clause 2: in_progress holds tickets with status in_progress."""
        from app.household import household_board
        
        # Create in_progress ticket
        ip_ticket = rules.create_ticket(db, 'her', {'title': 'In progress ticket'})
        rules.change_status(db, ip_ticket['id'], 'him', 'acknowledged')
        rules.change_status(db, ip_ticket['id'], 'him', 'in_progress')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['in_progress']) == 1
        assert result['in_progress'][0]['title'] == 'In progress ticket'

    def test_in_progress_excludes_other_statuses(self, db):
        """Clause 2: in_progress excludes tickets not in_progress."""
        from app.household import household_board
        
        # Create open ticket
        rules.create_ticket(db, 'her', {'title': 'Open ticket'})
        
        # Create done ticket
        done_ticket = rules.create_ticket(db, 'him', {'title': 'Done ticket'})
        rules.change_status(db, done_ticket['id'], 'her', 'acknowledged')
        rules.change_status(db, done_ticket['id'], 'her', 'in_progress')
        rules.change_status(db, done_ticket['id'], 'her', 'done')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['in_progress']) == 0

    def test_todo_ordered_oldest_created_at_first(self, db):
        """Clause 2: todo ordered oldest created_at first."""
        from app.household import household_board
        
        with patch('app.rules.datetime') as mock_datetime:
            # Create tickets in reverse chronological order
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 10, 0, tzinfo=rules.timezone.utc)
            ticket3 = rules.create_ticket(db, 'her', {'title': 'Third'})
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 9, 0, tzinfo=rules.timezone.utc)
            ticket2 = rules.create_ticket(db, 'him', {'title': 'Second'})
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 8, 0, tzinfo=rules.timezone.utc)
            ticket1 = rules.create_ticket(db, 'her', {'title': 'First'})
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['todo']) == 3
        assert result['todo'][0]['title'] == 'First'
        assert result['todo'][1]['title'] == 'Second'
        assert result['todo'][2]['title'] == 'Third'

    def test_in_progress_ordered_oldest_created_at_first(self, db):
        """Clause 2: in_progress ordered oldest created_at first."""
        from app.household import household_board
        
        with patch('app.rules.datetime') as mock_datetime:
            # Create and move tickets to in_progress in reverse order
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 10, 0, tzinfo=rules.timezone.utc)
            ticket3 = rules.create_ticket(db, 'her', {'title': 'Third'})
            rules.change_status(db, ticket3['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket3['id'], 'him', 'in_progress')
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 9, 0, tzinfo=rules.timezone.utc)
            ticket2 = rules.create_ticket(db, 'him', {'title': 'Second'})
            rules.change_status(db, ticket2['id'], 'her', 'acknowledged')
            rules.change_status(db, ticket2['id'], 'her', 'in_progress')
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 8, 0, tzinfo=rules.timezone.utc)
            ticket1 = rules.create_ticket(db, 'her', {'title': 'First'})
            rules.change_status(db, ticket1['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket1['id'], 'him', 'in_progress')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['in_progress']) == 3
        assert result['in_progress'][0]['title'] == 'First'
        assert result['in_progress'][1]['title'] == 'Second'
        assert result['in_progress'][2]['title'] == 'Third'

    def test_completed_contains_done_and_closed(self, db):
        """Clause 3: completed holds tickets with status done or closed."""
        from app.household import household_board
        
        # Create and complete a ticket (done)
        done_ticket = rules.create_ticket(db, 'her', {'title': 'Done ticket'})
        rules.change_status(db, done_ticket['id'], 'him', 'acknowledged')
        rules.change_status(db, done_ticket['id'], 'him', 'in_progress')
        rules.change_status(db, done_ticket['id'], 'him', 'done')
        
        # Create and close a ticket (closed)
        closed_ticket = rules.create_ticket(db, 'him', {'title': 'Closed ticket'})
        rules.change_status(db, closed_ticket['id'], 'her', 'acknowledged')
        rules.change_status(db, closed_ticket['id'], 'her', 'in_progress')
        rules.change_status(db, closed_ticket['id'], 'her', 'done')
        rules.change_status(db, closed_ticket['id'], 'him', 'closed')
        
        result = household_board(db, date(2024, 1, 15))
        
        completed_titles = {t['title'] for t in result['completed']}
        assert 'Done ticket' in completed_titles
        assert 'Closed ticket' in completed_titles
        assert len(result['completed']) == 2

    def test_completed_excludes_other_statuses(self, db):
        """Clause 3: completed excludes tickets not done or closed."""
        from app.household import household_board
        
        # Create open ticket
        rules.create_ticket(db, 'her', {'title': 'Open ticket'})
        
        # Create in_progress ticket
        ip_ticket = rules.create_ticket(db, 'him', {'title': 'In progress ticket'})
        rules.change_status(db, ip_ticket['id'], 'her', 'acknowledged')
        rules.change_status(db, ip_ticket['id'], 'her', 'in_progress')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['completed']) == 0

    def test_completed_within_7_day_window(self, db):
        """Clause 3: completed only includes tickets updated within 7 days (today + 6 before)."""
        from app.household import household_board
        
        with patch('app.rules.datetime') as mock_datetime:
            # Create ticket and complete it today (should be included)
            mock_datetime.now.return_value = rules.datetime(2024, 1, 15, 12, 0, tzinfo=rules.timezone.utc)
            ticket_today = rules.create_ticket(db, 'her', {'title': 'Today'})
            rules.change_status(db, ticket_today['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket_today['id'], 'him', 'in_progress')
            rules.change_status(db, ticket_today['id'], 'him', 'done')
            
            # Create ticket and complete it 6 days ago (should be included)
            mock_datetime.now.return_value = rules.datetime(2024, 1, 9, 12, 0, tzinfo=rules.timezone.utc)
            ticket_6_days = rules.create_ticket(db, 'him', {'title': 'Six days ago'})
            rules.change_status(db, ticket_6_days['id'], 'her', 'acknowledged')
            rules.change_status(db, ticket_6_days['id'], 'her', 'in_progress')
            rules.change_status(db, ticket_6_days['id'], 'her', 'done')
        
        result = household_board(db, date(2024, 1, 15))
        
        completed_titles = {t['title'] for t in result['completed']}
        assert 'Today' in completed_titles
        assert 'Six days ago' in completed_titles
        assert len(result['completed']) == 2

    def test_completed_excludes_outside_7_day_window(self, db):
        """Clause 3: completed excludes tickets updated more than 6 days before today."""
        from app.household import household_board
        
        with patch('app.rules.datetime') as mock_datetime:
            # Create ticket and complete it 7 days ago (should be excluded)
            mock_datetime.now.return_value = rules.datetime(2024, 1, 8, 12, 0, tzinfo=rules.timezone.utc)
            ticket_old = rules.create_ticket(db, 'her', {'title': 'Old ticket'})
            rules.change_status(db, ticket_old['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket_old['id'], 'him', 'in_progress')
            rules.change_status(db, ticket_old['id'], 'him', 'done')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['completed']) == 0

    def test_completed_ordered_newest_updated_at_first(self, db):
        """Clause 3: completed ordered newest updated_at first."""
        from app.household import household_board
        
        with patch('app.rules.datetime') as mock_datetime:
            # Create and complete tickets in chronological order
            mock_datetime.now.return_value = rules.datetime(2024, 1, 10, 12, 0, tzinfo=rules.timezone.utc)
            ticket1 = rules.create_ticket(db, 'her', {'title': 'First'})
            rules.change_status(db, ticket1['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket1['id'], 'him', 'in_progress')
            rules.change_status(db, ticket1['id'], 'him', 'done')
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 12, 12, 0, tzinfo=rules.timezone.utc)
            ticket2 = rules.create_ticket(db, 'him', {'title': 'Second'})
            rules.change_status(db, ticket2['id'], 'her', 'acknowledged')
            rules.change_status(db, ticket2['id'], 'her', 'in_progress')
            rules.change_status(db, ticket2['id'], 'her', 'done')
            
            mock_datetime.now.return_value = rules.datetime(2024, 1, 14, 12, 0, tzinfo=rules.timezone.utc)
            ticket3 = rules.create_ticket(db, 'her', {'title': 'Third'})
            rules.change_status(db, ticket3['id'], 'him', 'acknowledged')
            rules.change_status(db, ticket3['id'], 'him', 'in_progress')
            rules.change_status(db, ticket3['id'], 'him', 'done')
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['completed']) == 3
        assert result['completed'][0]['title'] == 'Third'
        assert result['completed'][1]['title'] == 'Second'
        assert result['completed'][2]['title'] == 'First'

    def test_empty_board_returns_empty_lists(self, db):
        """Edge case: no tickets returns empty lists for all columns."""
        from app.household import household_board
        
        result = household_board(db, date(2024, 1, 15))
        
        assert result['todo'] == []
        assert result['in_progress'] == []
        assert result['completed'] == []