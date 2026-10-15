import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock
from app.rules import dashboard, filed, ticket_to_dict
from app.models import Ticket


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.today = date(2024, 1, 1)

    def test_clause_1_dashboard_returns_correct_structure(self):
        """Clause 1: dashboard returns correct structure."""
        # Setup mock tickets
        tickets = [
            Ticket(
                id=1,
                title="Todo Ticket",
                details="",
                priority="normal",
                due=date(2024, 1, 5),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=2,
                title="In Progress Ticket",
                details="",
                priority="normal",
                due=None,
                status="in_progress",
                filed_by="him",
                assigned_to="her",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=3,
                title="Completed Ticket",
                details="",
                priority="normal",
                due=None,
                status="done",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        self.session.query().filter().all.return_value = tickets
        result = dashboard(self.session, "him", self.today)
        
        self.assertIn("todo", result)
        self.assertIn("in_progress", result)
        self.assertIn("completed", result)
        self.assertEqual(len(result["todo"]), 1)
        self.assertEqual(len(result["in_progress"]), 0)
        self.assertEqual(len(result["completed"]), 1)

    def test_clause_2_group_assignment(self):
        """Clause 2: group assignment based on priority and due date."""
        tickets = [
            Ticket(
                id=1,
                title="Urgent Ticket",
                details="",
                priority="urgent",
                due=date(2024, 1, 10),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=2,
                title="Due Today Ticket",
                details="",
                priority="normal",
                due=date(2024, 1, 1),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=3,
                title="Normal Ticket",
                details="",
                priority="normal",
                due=date(2024, 1, 10),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        self.session.query().filter().all.return_value = tickets
        result = dashboard(self.session, "him", self.today)
        
        self.assertEqual(result["todo"][0]["group"], 0)  # Urgent
        self.assertEqual(result["todo"][1]["group"], 1)  # Due today
        self.assertEqual(result["todo"][2]["group"], 2)  # Normal

    def test_clause_3_ordering(self):
        """Clause 3: ordering by group, due date, and created_at."""
        tickets = [
            Ticket(
                id=1,
                title="Ticket 1",
                details="",
                priority="urgent",
                due=date(2024, 1, 10),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=2,
                title="Ticket 2",
                details="",
                priority="normal",
                due=date(2024, 1, 1),
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=3,
                title="Ticket 3",
                details="",
                priority="normal",
                due=None,
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        self.session.query().filter().all.return_value = tickets
        result = dashboard(self.session, "him", self.today)
        
        self.assertEqual(result["todo"][0]["id"], 1)  # Group 0
        self.assertEqual(result["todo"][1]["id"], 2)  # Group 1
        self.assertEqual(result["todo"][2]["id"], 3)  # Group 2, no due date

    def test_clause_4_completed_tickets(self):
        """Clause 4: completed tickets with updated_at in the last 7 days."""
        tickets = [
            Ticket(
                id=1,
                title="Completed Ticket",
                details="",
                priority="normal",
                due=None,
                status="done",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=2,
                title="Old Completed Ticket",
                details="",
                priority="normal",
                due=None,
                status="done",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2023, 12, 25, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        self.session.query().filter().all.return_value = tickets
        result = dashboard(self.session, "him", self.today)
        
        self.assertEqual(len(result["completed"]), 1)
        self.assertEqual(result["completed"][0]["id"], 1)
        self.assertNotIn("group", result["completed"][0])

    def test_clause_5_filed_tickets(self):
        """Clause 5: filed returns tickets filed by user, newest first."""
        tickets = [
            Ticket(
                id=1,
                title="Old Ticket",
                details="",
                priority="normal",
                due=None,
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            ),
            Ticket(
                id=2,
                title="New Ticket",
                details="",
                priority="normal",
                due=None,
                status="open",
                filed_by="her",
                assigned_to="him",
                created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            ),
        ]
        
        self.session.query().filter().all.return_value = tickets
        result = filed(self.session, "her")
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 2)  # Newest first
        self.assertEqual(result[1]["id"], 1)


if __name__ == "__main__":
    unittest.main()
