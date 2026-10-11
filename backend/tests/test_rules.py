import unittest
import os
from datetime import datetime, date, timedelta, timezone
from unittest import mock
from sqlalchemy import text

# Import the components under test
from app.db import Base, SessionLocal, init_db
from app.models import Ticket
from app.rules import USERS, create_ticket, change_status, dashboard, filed

class TestTicketRules(unittest.TestCase):
    def setUp(self):
        self.db_url = os.getenv("TICKETER_DATABASE_URL")
        if not self.db_url:
            self.skipTest("TICKETER_DATABASE_URL not set")
        
        init_db()
        self.session = SessionLocal()

    def tearDown(self):
        if self.session:
            self.session.close()
            # Drop all tables to ensure isolation between tests
            self.session.execute(text("DROP TABLE IF EXISTS tickets"))
            self.session.commit()

    def test_db_config_raises_runtime_error_when_url_missing(self):
        """Clause 1: RuntimeError when TICKETER_DATABASE_URL is unset or empty"""
        # We must use a fresh process or reload the module because db.py 
        # executes the check at the module level during import.
        import importlib
        import app.db
        
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                importlib.reload(app.db)

    def test_ticket_model_columns(self):
        """Clause 2: Ticket model has correct columns and table name"""
        self.assertEqual(Ticket.__tablename__, "tickets")
        cols = Ticket.__table__.columns.keys()
        expected = ['id', 'title', 'details', 'priority', 'due', 'status', 'filed_by', 'assigned_to', 'created_at', 'updated_at']
        for col in expected:
            self.assertIn(col, cols)

    def test_create_ticket_success(self):
        """Clause 3: create_ticket success path"""
        data = {"title": "Fix the sink", "details": "Leaking", "priority": "urgent", "due": "2026-01-01"}
        ticket = create_ticket(self.session, "her", data)
        self.assertEqual(ticket['title'], "Fix the sink")
        self.assertEqual(ticket['assigned_to'], "him")
        self.assertEqual(ticket['status'], "open")
        self.assertIsInstance(ticket['created_at'], str)
        self.assertEqual(ticket['due'], "2026-01-01")

    def test_create_ticket_invalid_inputs(self):
        """Clause 4: create_ticket raises ValueError for bad inputs"""
        # Invalid user
        with self.assertRaises(ValueError): create_ticket(self.session, "stranger", {"title": "T"})
        # Missing title
        with self.assertRaises(ValueError): create_ticket(self.session, "her", {})
        # Title too long
        with self.assertRaises(ValueError): create_ticket(self.session, "her", {"title": "a" * 121})
        # Invalid priority
        with self.assertRaises(ValueError): create_ticket(self.session, "her", {"title": "T", "priority": "high"})
        # Invalid date
        with self.assertRaises(ValueError): create_ticket(self.session, "her", {"title": "T", "due": "not-a-date"})
        # Extra key
        with self.assertRaises(ValueError): create_ticket(self.session, "her", {"title": "T", "extra": "x"})

    def test_change_status_success(self):
        """Clause 5: change_status applies valid moves"""
        t = create_ticket(self.session, "her", {"title": "T"})
        # open -> acknowledged (assignee)
        updated = change_status(self.session, t['id'], "him", "acknowledged")
        self.assertEqual(updated['status'], "acknowledged")

    def test_change_status_errors(self):
        """Clause 6: change_status raises LookupError, ValueError, PermissionError"""
        t = create_ticket(self.session, "her", {"title": "T"})
        # LookupError: non-existent
        with self.assertRaises(LookupError): change_status(self.session, 999, "him", "acknowledged")
        # LookupError: not a party
        with self.assertRaises(LookupError): change_status(self.session, t['id'], "stranger", "acknowledged")
        # ValueError: unknown status
        with self.assertRaises(ValueError): change_status(self.session, t['id'], "him", "ghost")
        # ValueError: invalid move
        with self.assertRaises(ValueError): change_status(self.session, t['id'], "him", "closed")
        # PermissionError: wrong party (filer cannot acknowledge)
        with self.assertRaises(PermissionError): change_status(self.session, t['id'], "her", "acknowledged")

    def test_dashboard_sorting_and_grouping(self):
        """Clause 7: dashboard grouping and ordering"""
        today = date(2026, 1, 1)
        # Urgent/Overdue (Group 0)
        create_ticket(self.session, "her", {"title": "T1", "priority": "urgent", "due": "2026-01-01"})
        # Near future (Group 1)
        create_ticket(self.session, "her", {"title": "T2", "priority": "normal", "due": "2026-01-03"})
        # Far future (Group 2)
        create_ticket(self.session, "her", {"title": "T3", "priority": "normal", "due": "2026-02-01"})
        
        dash = dashboard(self.session, "him", today)
        self.assertEqual(dash['todo'][0]['title'], "T1")
        self.assertEqual(dash['todo'][0]['group'], 0)
        self.assertEqual(dash['todo'][1]['title'], "T2")
        self.assertEqual(dash['todo'][1]['group'], 1)
        self.assertEqual(dash['todo'][2]['title'], "T3")
        self.assertEqual(dash['todo'][2]['group'], 2)

    def test_dashboard_completed_window(self):
        """Clause 8: completed tickets within 7 day window"""
        today = date(2026, 1, 10)
        # Ticket 1: Updated today (In window)
        t1 = create_ticket(self.session, "her", {"title": "T1"})
        ticket1 = self.session.get(Ticket, t1['id'])
        ticket1.status = "done"
        ticket1.updated_at = datetime(2026, 1, 10, tzinfo=timezone.utc)
        self.session.commit()

        # Ticket 2: Updated 7 days ago (In window)
        t2 = create_ticket(self.session, "her", {"title": "T2"})
        ticket2 = self.session.get(Ticket, t2['id'])
        ticket2.status = "done"
        ticket2.updated_at = datetime(2026, 1, 3, tzinfo=timezone.utc)
        self.session.commit()

        # Ticket 3: Updated 8 days ago (Out of window)
        t3 = create_ticket(self.session, "her", {"title": "T3"})
        ticket3 = self.session.get(Ticket, t3['id'])
        ticket3.status = "done"
        ticket3.updated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.session.commit()

        dash = dashboard(self.session, "him", today)
        completed_titles = [t['title'] for t in dash['completed']]
        self.assertIn("T1", completed_titles)
        self.assertIn("T2", completed_titles)
        self.assertNotIn("T3", completed_titles)
        self.assertEqual(completed_titles[0], "T1") # Newest first

    def test_filed_tickets(self):
        """Clause 9: filed(session, user) returns tickets user filed"""
        create_ticket(self.session, "her", {"title": "T1"})
        create_ticket(self.session, "her", {"title": "T2"})
        create_ticket(self.session, "him", {"title": "T3"})
        
        her_filed = filed(self.session, "her")
        self.assertEqual(len(her_filed), 2)
        self.assertEqual(her_filed[0]['title'], "T2") # Newest first
