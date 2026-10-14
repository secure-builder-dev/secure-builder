from datetime import date, datetime, timezone, timedelta
import pytest

from app.rules import dashboard, filed, ticket_to_dict
from app.models import Ticket


class TestDashboard:
    """Tests for rules.dashboard function."""
    
    def test_dashboard_returns_correct_structure(self, db):
        """Clause 1: dashboard returns dict with todo, in_progress, completed keys."""
        today = date(2025, 6, 15)
        result = dashboard(db, 'her', today)
        
        assert isinstance(result, dict)
        assert set(result.keys()) == {'todo', 'in_progress', 'completed'}
        assert isinstance(result['todo'], list)
        assert isinstance(result['in_progress'], list)
        assert isinstance(result['completed'], list)
    
    def test_dashboard_only_assigned_tickets(self, db):
        """Clause 1: dashboard returns only tickets assigned to user."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Create ticket assigned to 'her'
        ticket_her = Ticket(
            title='Her ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ticket_her)
        
        # Create ticket assigned to 'him'
        ticket_him = Ticket(
            title='Him ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now,
            updated_at=now
        )
        db.add(ticket_him)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        # Only her's ticket should appear
        all_tickets = [t for col in result.values() for t in col]
        assert len(all_tickets) == 1
        assert all_tickets[0]['id'] == ticket_her.id
    
    def test_todo_contains_open_and_acknowledged(self, db):
        """Clause 2: todo holds tickets with status open or acknowledged."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Open ticket
        open_ticket = Ticket(
            title='Open ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(open_ticket)
        
        # Acknowledged ticket
        ack_ticket = Ticket(
            title='Acknowledged ticket',
            details='',
            priority='normal',
            due=None,
            status='acknowledged',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ack_ticket)
        
        # In progress ticket (should NOT be in todo)
        ip_ticket = Ticket(
            title='In progress ticket',
            details='',
            priority='normal',
            due=None,
            status='in_progress',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ip_ticket)
        
        # Done ticket (should NOT be in todo)
        done_ticket = Ticket(
            title='Done ticket',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(done_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        todo_ids = {t['id'] for t in result['todo']}
        assert open_ticket.id in todo_ids
        assert ack_ticket.id in todo_ids
        assert ip_ticket.id not in todo_ids
        assert done_ticket.id not in todo_ids
    
    def test_in_progress_contains_only_in_progress(self, db):
        """Clause 2: in_progress holds tickets with status in_progress."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # In progress ticket
        ip_ticket = Ticket(
            title='In progress ticket',
            details='',
            priority='normal',
            due=None,
            status='in_progress',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ip_ticket)
        
        # Open ticket (should NOT be in in_progress)
        open_ticket = Ticket(
            title='Open ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(open_ticket)
        
        # Done ticket (should NOT be in in_progress)
        done_ticket = Ticket(
            title='Done ticket',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(done_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        ip_ids = {t['id'] for t in result['in_progress']}
        assert ip_ticket.id in ip_ids
        assert open_ticket.id not in ip_ids
        assert done_ticket.id not in ip_ids
    
    def test_group_0_for_urgent_priority(self, db):
        """Clause 2: group is 0 when priority is urgent."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        urgent_ticket = Ticket(
            title='Urgent ticket',
            details='',
            priority='urgent',
            due=date(2025, 7, 1),  # Far in future
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(urgent_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 0
    
    def test_group_0_for_due_before_today(self, db):
        """Clause 2: group is 0 when due is before today."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        overdue_ticket = Ticket(
            title='Overdue ticket',
            details='',
            priority='low',  # Not urgent
            due=date(2025, 6, 10),  # Before today
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(overdue_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 0
    
    def test_group_1_for_due_today(self, db):
        """Clause 2: group is 1 when due is today."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        due_today_ticket = Ticket(
            title='Due today ticket',
            details='',
            priority='low',
            due=date(2025, 6, 15),  # Today
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(due_today_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 1
    
    def test_group_1_for_due_within_3_days(self, db):
        """Clause 2: group is 1 when due is within 3 days after today."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Due in 3 days (within the window)
        due_in_3_days = Ticket(
            title='Due in 3 days',
            details='',
            priority='low',
            due=date(2025, 6, 18),  # Today + 3 days
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(due_in_3_days)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 1
    
    def test_group_2_for_due_after_3_days(self, db):
        """Clause 2: group is 2 when due is more than 3 days after today."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        due_later_ticket = Ticket(
            title='Due later ticket',
            details='',
            priority='low',
            due=date(2025, 6, 20),  # More than 3 days after today
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(due_later_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 2
    
    def test_group_2_for_no_due_date(self, db):
        """Clause 2: group is 2 when there is no due date."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        no_due_ticket = Ticket(
            title='No due ticket',
            details='',
            priority='low',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(no_due_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert result['todo'][0]['group'] == 2
    
    def test_ordering_by_group_then_due_then_created(self, db):
        """Clause 3: todo and in_progress ordered by group, then due (none last), then created_at."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Group 0: urgent
        t1 = Ticket(
            title='Urgent',
            details='',
            priority='urgent',
            due=date(2025, 7, 1),
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now + timedelta(hours=3),
            updated_at=now
        )
        
        # Group 0: overdue
        t2 = Ticket(
            title='Overdue',
            details='',
            priority='low',
            due=date(2025, 6, 10),
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now + timedelta(hours=1),
            updated_at=now
        )
        
        # Group 1: due today
        t3 = Ticket(
            title='Due today',
            details='',
            priority='low',
            due=date(2025, 6, 15),
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now + timedelta(hours=2),
            updated_at=now
        )
        
        # Group 2: no due date
        t4 = Ticket(
            title='No due',
            details='',
            priority='low',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now + timedelta(hours=4),
            updated_at=now
        )
        
        # Group 2: far future due
        t5 = Ticket(
            title='Far future',
            details='',
            priority='low',
            due=date(2025, 7, 1),
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now + timedelta(hours=5),
            updated_at=now
        )
        
        db.add_all([t1, t2, t3, t4, t5])
        db.commit()
        
        result = dashboard(db, 'her', today)
        todo = result['todo']
        
        # Should be ordered: group 0 (t2, t1), group 1 (t3), group 2 with due (t5), group 2 no due (t4)
        # Within group 0: ordered by due date ascending. t2.due=6/10 < t1.due=7/1, so t2 first
        assert len(todo) == 5
        assert todo[0]['id'] == t2.id  # Group 0, due 6/10 (overdue)
        assert todo[1]['id'] == t1.id  # Group 0, due 7/1 (urgent)
        assert todo[2]['id'] == t3.id  # Group 1, due today
        assert todo[3]['id'] == t5.id  # Group 2, due 7/1
        assert todo[4]['id'] == t4.id  # Group 2, no due (last)
    
    def test_completed_contains_done_and_closed(self, db):
        """Clause 4: completed holds tickets with status done or closed."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Done ticket updated today
        done_ticket = Ticket(
            title='Done ticket',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        db.add(done_ticket)
        
        # Closed ticket updated today
        closed_ticket = Ticket(
            title='Closed ticket',
            details='',
            priority='normal',
            due=None,
            status='closed',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        db.add(closed_ticket)
        
        # Open ticket (should NOT be in completed)
        open_ticket = Ticket(
            title='Open ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(open_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        completed_ids = {t['id'] for t in result['completed']}
        assert done_ticket.id in completed_ids
        assert closed_ticket.id in completed_ids
        assert open_ticket.id not in completed_ids
    
    def test_completed_within_7_day_window(self, db):
        """Clause 4: completed only includes tickets updated today or within 6 days before."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Updated today (within window)
        t1 = Ticket(
            title='Updated today',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        # Updated 6 days ago (within window)
        t2 = Ticket(
            title='Updated 6 days ago',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=6)
        )
        
        # Updated 7 days ago (outside window)
        t3 = Ticket(
            title='Updated 7 days ago',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=7)
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        completed_ids = {t['id'] for t in result['completed']}
        assert t1.id in completed_ids
        assert t2.id in completed_ids
        assert t3.id not in completed_ids
    
    def test_completed_ordered_newest_updated_first(self, db):
        """Clause 4: completed ordered by newest updated_at first."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Updated most recently
        t1 = Ticket(
            title='Most recent',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        
        # Updated earlier
        t2 = Ticket(
            title='Earlier',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=2)
        )
        
        # Updated earliest
        t3 = Ticket(
            title='Earliest',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=5)
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = dashboard(db, 'her', today)
        completed = result['completed']
        
        assert len(completed) == 3
        assert completed[0]['id'] == t1.id  # Most recent
        assert completed[1]['id'] == t2.id  # Middle
        assert completed[2]['id'] == t3.id  # Earliest
    
    def test_completed_has_no_group_key(self, db):
        """Clause 4: completed tickets do not have a group key."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        done_ticket = Ticket(
            title='Done ticket',
            details='',
            priority='normal',
            due=None,
            status='done',
            filed_by='him',
            assigned_to='her',
            created_at=now - timedelta(days=10),
            updated_at=now
        )
        db.add(done_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['completed']) == 1
        assert 'group' not in result['completed'][0]
    
    def test_todo_has_group_key(self, db):
        """Clause 2: todo tickets have a group key."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        open_ticket = Ticket(
            title='Open ticket',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(open_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['todo']) == 1
        assert 'group' in result['todo'][0]
    
    def test_in_progress_has_group_key(self, db):
        """Clause 2: in_progress tickets have a group key."""
        today = date(2025, 6, 15)
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        ip_ticket = Ticket(
            title='In progress ticket',
            details='',
            priority='normal',
            due=None,
            status='in_progress',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ip_ticket)
        db.commit()
        
        result = dashboard(db, 'her', today)
        
        assert len(result['in_progress']) == 1
        assert 'group' in result['in_progress'][0]
    
    def test_dashboard_with_no_tickets(self, db):
        """Clause 1: dashboard returns empty lists when no tickets exist."""
        today = date(2025, 6, 15)
        result = dashboard(db, 'her', today)
        
        assert result['todo'] == []
        assert result['in_progress'] == []
        assert result['completed'] == []


class TestFiled:
    """Tests for rules.filed function."""
    
    def test_filed_returns_tickets_user_filed(self, db):
        """Clause 5: filed returns tickets user filed."""
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Ticket filed by 'her'
        ticket_her = Ticket(
            title='Her filed',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now,
            updated_at=now
        )
        db.add(ticket_her)
        
        # Ticket filed by 'him'
        ticket_him = Ticket(
            title='Him filed',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='him',
            assigned_to='her',
            created_at=now,
            updated_at=now
        )
        db.add(ticket_him)
        db.commit()
        
        result = filed(db, 'her')
        
        assert len(result) == 1
        assert result[0]['id'] == ticket_her.id
    
    def test_filed_returns_all_statuses(self, db):
        """Clause 5: filed returns tickets regardless of status."""
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        statuses = ['open', 'acknowledged', 'in_progress', 'done', 'closed']
        tickets = []
        for i, status in enumerate(statuses):
            ticket = Ticket(
                title=f'Ticket {status}',
                details='',
                priority='normal',
                due=None,
                status=status,
                filed_by='her',
                assigned_to='him',
                created_at=now + timedelta(hours=i),
                updated_at=now
            )
            tickets.append(ticket)
            db.add(ticket)
        db.commit()
        
        result = filed(db, 'her')
        
        assert len(result) == 5
        result_statuses = {t['status'] for t in result}
        assert result_statuses == set(statuses)
    
    def test_filed_ordered_newest_created_first(self, db):
        """Clause 5: filed ordered by newest created_at first."""
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        # Created earliest
        t1 = Ticket(
            title='Earliest',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now - timedelta(days=5),
            updated_at=now
        )
        
        # Created middle
        t2 = Ticket(
            title='Middle',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now - timedelta(days=2),
            updated_at=now
        )
        
        # Created most recently
        t3 = Ticket(
            title='Most recent',
            details='',
            priority='normal',
            due=None,
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now,
            updated_at=now
        )
        
        db.add_all([t1, t2, t3])
        db.commit()
        
        result = filed(db, 'her')
        
        assert len(result) == 3
        assert result[0]['id'] == t3.id  # Most recent
        assert result[1]['id'] == t2.id  # Middle
        assert result[2]['id'] == t1.id  # Earliest
    
    def test_filed_with_no_tickets(self, db):
        """Clause 5: filed returns empty list when user has no tickets."""
        result = filed(db, 'her')
        assert result == []
    
    def test_filed_returns_ticket_to_dict_format(self, db):
        """Clause 5: filed returns ticket_to_dict format."""
        now = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
        
        ticket = Ticket(
            title='Test ticket',
            details='Some details',
            priority='urgent',
            due=date(2025, 6, 20),
            status='open',
            filed_by='her',
            assigned_to='him',
            created_at=now,
            updated_at=now
        )
        db.add(ticket)
        db.commit()
        
        result = filed(db, 'her')
        
        assert len(result) == 1
        ticket_dict = result[0]
        
        # Check all expected keys from ticket_to_dict
        assert 'id' in ticket_dict
        assert 'title' in ticket_dict
        assert 'details' in ticket_dict
        assert 'priority' in ticket_dict
        assert 'status' in ticket_dict
        assert 'filed_by' in ticket_dict
        assert 'assigned_to' in ticket_dict
        assert 'due' in ticket_dict
        assert 'created_at' in ticket_dict
        assert 'updated_at' in ticket_dict
        
        # Check values
        assert ticket_dict['title'] == 'Test ticket'
        assert ticket_dict['details'] == 'Some details'
        assert ticket_dict['priority'] == 'urgent'
        assert ticket_dict['due'] == '2025-06-20'
        assert ticket_dict['status'] == 'open'
        assert ticket_dict['filed_by'] == 'her'
        assert ticket_dict['assigned_to'] == 'him'
        
        # Check timestamps are ISO format strings
        assert isinstance(ticket_dict['created_at'], str)
        assert isinstance(ticket_dict['updated_at'], str)