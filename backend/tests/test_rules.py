import unittest
import os
from datetime import datetime, date, timedelta, timezone
from unittest import mock

# We import these inside tests or use mock because the files don't exist yet
# and the goal is to write tests that FAIL until the behavior exists.

class TestTicketerRules(unittest.TestCase):
    def setUp(self):
        # This will fail because app.db and app.rules don't exist
        from app.db import init_db, SessionLocal
        from app.rules import USERS
        
        self.session = SessionLocal()
        init_db()
        self.users = USERS

    def tearDown(self):
        # This will fail because app.db doesn't exist
        from app.db import Base, engine
        Base.metadata.drop_all(bind=engine)
        self.session.close()

    def test_db_url_missing_raises_runtime_error(self):
        # Test Clause 1: RuntimeError when TICKETER_DATABASE_URL is unset/empty
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                import importlib
                import app.db
                importlib.reload(app.db)

    def test_create_ticket_success(self):
        # Test Clause 3: Success case for create_ticket
        from app.rules import create_ticket
        data = {
            "title": "Fix the sink",
            "details": "Leaking in the kitchen",
            "priority": "urgent",
            "due": "2026-01-01"
        }
        ticket = create_ticket(self.session, "her", data)
        self.assertEqual(ticket["title"], "Fix the sink")
        self.assertEqual(ticket["assigned_to"], "him")
        self.assertEqual(ticket["status"], "open")
        self.assertIsInstance(ticket["created_at"], str)

    def test_create_ticket_invalid_inputs(self):
        # Test Clause 4: Rejection cases for create_ticket
        from app.rules import create_ticket
        
        # Invalid user
        with self.assertRaises(ValueError):
            create_ticket(self.session, "intruder", {"title": "Valid"})
        
        # Missing title
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"details": "No title"})
        
        # Title too long
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "a" * 121})
        
        # Invalid priority
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "priority": "extreme"})
        
        # Invalid date
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "due": "not-a-date"})
        
        # Extra keys
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "hack": "me"})

    def test_change_status_flow(self):
        # Test Clause 5: Valid status moves
        from app.rules import create_ticket, change_status
        t = create_ticket(self.session, "her", {"title": "Task"})
        
        # open -> acknowledged (assignee)
        updated = change_status(self.session, t["id"], "him", "acknowledged")
        self.assertEqual(updated["status"], "acknowledged")

    def test_change_status_errors(self):
        # Test Clause 6: Rejection cases for change_status
        from app.rules import create_ticket, change_status
        t = create_ticket(self.session, "her", {"title": "Task"})
        
        # LookupError: Ticket doesn't exist
        with self.assertRaises(LookupError):
            change_status(self.session, 999, "him", "acknowledged")
        
        # LookupError: User not party
        with self.assertRaises(LookupError):
            change_status(self.session, t["id"], "stranger", "acknowledged")
        
        # ValueError: Unknown status
        with self.assertRaises(ValueError):
            change_status(self.session, t["id"], "him", "deleted")
        
        # PermissionError: Wrong party (filer cannot acknowledge)
        with self.assertRaises(PermissionError):
            change_status(self.session, t["id"], "her", "acknowledged")

    def test_dashboard_sorting_and_grouping(self):
        # Test Clause 7 & 8: Dashboard logic
        from app.rules import create_ticket, change_status, dashboard
        today = date(2026, 1, 1)
        
        # Ticket 1: Urgent (Group 0)
        t1 = create_ticket(self.session, "her", {"title": "T1", "priority": "urgent"})
        # Ticket 2: Due today (Group 1)
        t2 = create_ticket(self.session, "her", {"title": "T2", "due": "2026-01-01"})
        # Ticket 3: Due later (Group 2)
        t3 = create_ticket(self.session, "her", {"title": "T3", "due": "2026-01-10"})
        
        dash = dashboard(self.session, "him", today)
        self.assertEqual(dash["todo"][0]["title"], "T1")
        self.assertEqual(dash["todo"][0]["group"], 0)
        self.assertEqual(dash["todo"][1]["title"], "T2")
        self.assertEqual(dash["todo"][1]["group"], 1)
        self.assertEqual(dash["todo"][2]["title"], "T3")
        self.assertEqual(dash["todo"][2]["group"], 2)

    def test_filed_tickets(self):
        # Test Clause 9: filed() returns tickets user filed
        from app.rules import create_ticket, filed
        create_ticket(self.session, "her", {"title": "H1"})
        create_ticket(self.session, "her", {"title": "H2"})
        create_ticket(self.session, "him", {"title": "M1"})
        
        her_filed = filed(self.session, "her")
        self.assertEqual(len(her_filed), 2)
        self.assertEqual(her_filed[0]["title"], "H2") # Newest first
