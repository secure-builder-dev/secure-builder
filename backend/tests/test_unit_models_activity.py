import unittest
from sqlalchemy import inspect
from app import db

class TestCommentModel(unittest.TestCase):
    def test_comment_model_columns(self):
        # Import Comment; should exist
        from app.models import Comment
        # Verify table name
        self.assertEqual(Comment.__tablename__, "comments")
        # Expected columns
        cols = {c.name: c for c in Comment.__table__.columns}
        expected = {
            "id": ("Integer", True),
            "ticket_id": ("Integer", False),
            "author": ("String", False),
            "body": ("String", False),
            "created_at": ("DateTime", False),
        }
        for name, (type_name, primary) in expected.items():
            self.assertIn(name, cols, f"Missing column {name}")
            col = cols[name]
            self.assertEqual(col.primary_key, primary, f"{name} primary_key")
            # Check type class name
            self.assertEqual(col.type.__class__.__name__, type_name, f"{name} type")
        # Check foreign key on ticket_id
        fks = [fk for fk in cols["ticket_id"].foreign_keys]
        self.assertTrue(any("tickets.id" in str(fk.column) for fk in fks), "ticket_id foreign key")

class TestTicketEventModel(unittest.TestCase):
    def test_ticket_event_model_columns(self):
        from app.models import TicketEvent
        self.assertEqual(TicketEvent.__tablename__, "ticket_events")
        cols = {c.name: c for c in TicketEvent.__table__.columns}
        expected = {
            "id": ("Integer", True),
            "ticket_id": ("Integer", False),
            "actor": ("String", False),
            "kind": ("String", False),
            "from_status": ("String", False),
            "to_status": ("String", False),
            "at": ("DateTime", False),
        }
        for name, (type_name, primary) in expected.items():
            self.assertIn(name, cols, f"Missing column {name}")
            col = cols[name]
            self.assertEqual(col.primary_key, primary, f"{name} primary_key")
            self.assertEqual(col.type.__class__.__name__, type_name, f"{name} type")
        # foreign key on ticket_id
        fks = [fk for fk in cols["ticket_id"].foreign_keys]
        self.assertTrue(any("tickets.id" in str(fk.column) for fk in fks), "ticket_id foreign key")

class TestInitDbCreatesTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure DB is initialized
        db.init_db()
        cls.inspector = inspect(db.engine)

    def test_comments_table_exists(self):
        self.assertTrue(self.inspector.has_table("comments"), "comments table not created")

    def test_ticket_events_table_exists(self):
        self.assertTrue(self.inspector.has_table("ticket_events"), "ticket_events table not created")

    def test_ticket_model_unchanged(self):
        from app.models import Ticket
        cols = {c.name for c in Ticket.__table__.columns}
        expected = {"id","title","details","priority","due","status","filed_by","assigned_to","created_at","updated_at"}
        self.assertEqual(cols, expected)

if __name__ == "__main__":
    unittest.main()
