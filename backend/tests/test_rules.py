import unittest
import os
from datetime import datetime, date, timedelta, timezone
from unittest import mock

class TestTicketerRules(unittest.TestCase):
    def setUp(self):
        from app.db import init_db, SessionLocal, Base, engine
        # Ensure tables are created before opening a session
        Base.metadata.create_all(bind=engine)
        self.session = SessionLocal()
        from app.rules import USERS
        self.users = USERS

    def tearDown(self):
        from app.db import Base, engine
        # Close session BEFORE dropping tables to avoid IdleInTransactionSessionTimeout
        if hasattr(self, 'session'):
            self.session.close()
        Base.metadata.drop_all(bind=engine)

    def test_db_url_missing_raises_runtime_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                import importlib
                import app.db
                importlib.reload(app.db)

    def test_create_ticket_success(self):
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
        from app.rules import create_ticket
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "intruder", {"title": "Valid"})
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"details": "No title"})
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "a" * 121})
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "priority": "extreme"})
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "due": "not-a-date"})
        
        with self.assertRaises(ValueError):
            create_ticket(self.session, "her", {"title": "Valid", "hack": "me"})

    def test_change_status_flow(self):
        from app.rules import create_ticket, change_status
        t = create_ticket(self.session, "her", {"title": "Task"})
        
        updated = change_status(self.session, t["id"], "him", "acknowledged")
        self.assertEqual(updated["status"], "acknowledged")

    def test_change_status_errors(self):
        from app.rules import create_ticket, change_status
        t = create_ticket(self.session, "her", {"title": "Task"})
        
        with self.assertRaises(LookupError):
            change_status(self.session, 999, "him", "acknowledged")
        
        with self.assertRaises(LookupError):
            change_status(self.session, t["id"], "stranger", "acknowledged")
        
        with self.assertRaises(ValueError):
            change_status(self.session, t["id"], "him", "deleted")
        
        with self.assertRaises(PermissionError):
            change_status(self.session, t["id"], "her", "acknowledged")

    def test_dashboard_sorting_and_grouping(self):
        from app.rules import create_ticket, dashboard
        today = date(2026, 1, 1)
        
        t1 = create_ticket(self.session, "her", {"title": "T1", "priority": "urgent"})
        t2 = create_ticket(self.session, "her", {"title": "T2", "due": "2026-01-01"})
        t3 = create_ticket(self.session, "her", {"title": "T3", "due": "2026-01-10"})
        
        dash = dashboard(self.session, "him", today)
        self.assertEqual(dash["todo"][0]["title"], "T1")
        self.assertEqual(dash["todo"][0]["group"], 0)
        self.assertEqual(dash["todo"][1]["title"], "T2")
        self.assertEqual(dash["todo"][1]["group"], 1)
        self.assertEqual(dash["todo"][2]["title"], "T3")
        self.assertEqual(dash["todo"][2]["group"], 2)

    def test_filed_tickets(self):
        from app.rules import create_ticket, filed
        create_ticket(self.session, "her", {"title": "H1"})
        create_ticket(self.session, "her", {"title": "H2"})
        create_ticket(self.session, "him", {"title": "M1"})
        
        her_filed = filed(self.session, "her")
        self.assertEqual(len(her_filed), 2)
        self.assertEqual(her_filed[0]["title"], "H2")
