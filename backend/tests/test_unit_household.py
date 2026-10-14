from datetime import date, timedelta, datetime, timezone
from unittest.mock import patch

import pytest

from app.models import Ticket
from app import rules
from tests.conftest import set_times


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
        from sqlalchemy import text
        
        # Create tickets with explicit timestamps using raw SQL for precise control
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('First', '', 'normal', NULL, 'open', 'her', 'him', '2024-01-15 08:00:00+00', '2024-01-15 08:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Second', '', 'normal', NULL, 'open', 'him', 'her', '2024-01-15 09:00:00+00', '2024-01-15 09:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Third', '', 'normal', NULL, 'open', 'her', 'him', '2024-01-15 10:00:00+00', '2024-01-15 10:00:00+00')
        """))
        db.commit()
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['todo']) == 3
        assert result['todo'][0]['title'] == 'First'
        assert result['todo'][1]['title'] == 'Second'
        assert result['todo'][2]['title'] == 'Third'

    def test_in_progress_ordered_oldest_created_at_first(self, db):
        """Clause 2: in_progress ordered oldest created_at first."""
        from app.household import household_board
        from sqlalchemy import text
        
        # Create tickets with explicit timestamps and move them to in_progress
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Third', '', 'normal', NULL, 'in_progress', 'her', 'him', '2024-01-15 10:00:00+00', '2024-01-15 10:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Second', '', 'normal', NULL, 'in_progress', 'him', 'her', '2024-01-15 09:00:00+00', '2024-01-15 09:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('First', '', 'normal', NULL, 'in_progress', 'her', 'him', '2024-01-15 08:00:00+00', '2024-01-15 08:00:00+00')
        """))
        db.commit()
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['in_progress']) == 3
        assert result['in_progress'][0]['title'] == 'First'
        assert result['in_progress'][1]['title'] == 'Second'
        assert result['in_progress'][2]['title'] == 'Third'

    def test_completed_contains_done_and_closed(self, db):
        """Clause 3: completed holds tickets with status done or closed."""
        from app.household import household_board
        from sqlalchemy import text
        
        # Create tickets with explicit timestamps within the 7-day window
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Done ticket', '', 'normal', NULL, 'done', 'her', 'him', '2024-01-10 10:00:00+00', '2024-01-15 10:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Closed ticket', '', 'normal', NULL, 'closed', 'him', 'her', '2024-01-10 10:00:00+00', '2024-01-15 11:00:00+00')
        """))
        db.commit()
        
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
        from sqlalchemy import text
        
        # Create ticket and complete it today (should be included)
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Today', '', 'normal', NULL, 'done', 'her', 'him', '2024-01-15 12:00:00+00', '2024-01-15 12:00:00+00')
        """))
        
        # Create ticket and complete it 6 days ago (should be included)
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Six days ago', '', 'normal', NULL, 'done', 'him', 'her', '2024-01-09 12:00:00+00', '2024-01-09 12:00:00+00')
        """))
        db.commit()
        
        result = household_board(db, date(2024, 1, 15))
        
        completed_titles = {t['title'] for t in result['completed']}
        assert 'Today' in completed_titles
        assert 'Six days ago' in completed_titles
        assert len(result['completed']) == 2

    def test_completed_excludes_outside_7_day_window(self, db):
        """Clause 3: completed excludes tickets updated more than 6 days before today."""
        from app.household import household_board
        from sqlalchemy import text
        
        # Create ticket and complete it 7 days ago (should be excluded)
        # Window is Jan 9-15, so Jan 8 is outside
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Old ticket', '', 'normal', NULL, 'done', 'her', 'him', '2024-01-08 12:00:00+00', '2024-01-08 12:00:00+00')
        """))
        db.commit()
        
        result = household_board(db, date(2024, 1, 15))
        
        assert len(result['completed']) == 0

    def test_completed_ordered_newest_updated_at_first(self, db):
        """Clause 3: completed ordered newest updated_at first."""
        from app.household import household_board
        from sqlalchemy import text
        
        # Create and complete tickets in chronological order with explicit timestamps
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('First', '', 'normal', NULL, 'done', 'her', 'him', '2024-01-05 12:00:00+00', '2024-01-10 12:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Second', '', 'normal', NULL, 'done', 'him', 'her', '2024-01-06 12:00:00+00', '2024-01-12 12:00:00+00')
        """))
        db.execute(text("""
            INSERT INTO tickets (title, details, priority, due, status, filed_by, assigned_to, created_at, updated_at)
            VALUES ('Third', '', 'normal', NULL, 'done', 'her', 'him', '2024-01-07 12:00:00+00', '2024-01-14 12:00:00+00')
        """))
        db.commit()
        
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