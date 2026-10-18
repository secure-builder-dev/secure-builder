import unittest
import datetime
from datetime import timezone

# Import the function under test. It may not exist yet; the import will succeed if the module is present.
# If the module does not exist, the test will fail on the first assertion.
from app import household as household_module
from app import rules
from app.models import Ticket

class FakeQuery:
    def __init__(self, items):
        self._items = items
    def filter(self, *args, **kwargs):
        # household_board is expected to call .filter(...).all() but we ignore the filter criteria.
        return self
    def all(self):
        return self._items

class FakeSession:
    def __init__(self, tickets):
        self._tickets = tickets
    def query(self, model):
        # Assume model is Ticket; return a FakeQuery over the provided tickets.
        return FakeQuery(self._tickets)

class TestHouseholdBoard(unittest.TestCase):
    def setUp(self):
        # Common "today" used for all tests.
        self.today = datetime.date(2023, 1, 10)
        # Helper to create a Ticket instance with minimal required fields.
        def make_ticket(id, title, status, filed_by, assigned_to, created_at, updated_at, priority="normal", due=None):
            t = Ticket(
                id=id,
                title=title,
                details="",
                priority=priority,
                due=due,
                status=status,
                filed_by=filed_by,
                assigned_to=assigned_to,
                created_at=created_at,
                updated_at=updated_at,
            )
            return t
        self.make_ticket = make_ticket

    def test_household_board_exists_and_structure(self):
        """Clause 1 – the function exists and returns the correct top‑level keys.
        It must return a dict with exactly the keys 'todo', 'in_progress', and 'completed',
        each mapping to a list.  Each ticket dict must be produced by rules.ticket_to_dict
        and must **not** contain a 'group' key.
        """
        # Ensure the function is present.
        self.assertTrue(hasattr(household_module, "household_board"), "household_board function is missing")
        # Create a minimal session with a single ticket.
        created = datetime.datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
        ticket = self.make_ticket(
            id=1,
            title="Test",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=created,
            updated_at=created,
        )
        session = FakeSession([ticket])
        board = household_module.household_board(session, self.today)
        # Verify top‑level structure.
        self.assertIsInstance(board, dict)
        self.assertCountEqual(board.keys(), ["todo", "in_progress", "completed"])
        for col in ["todo", "in_progress", "completed"]:
            self.assertIsInstance(board[col], list)
        # Verify the ticket appears in the correct column (status "open" -> todo).
        self.assertEqual(len(board["todo"]), 1)
        ticket_dict = board["todo"][0]
        # It must be the dict produced by rules.ticket_to_dict.
        expected = rules.ticket_to_dict(ticket)
        self.assertEqual(ticket_dict, expected)
        # No 'group' key should be present.
        self.assertNotIn("group", ticket_dict)

    def test_household_board_todo_in_progress_ordering(self):
        """Clause 2 – todo and in_progress columns are ordered by oldest created_at first.
        We create multiple tickets with distinct created_at timestamps and verify the order.
        """
        # Create tickets for both users.
        t1 = self.make_ticket(
            id=1,
            title="Old Todo",
            status="open",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.datetime(2023, 1, 1, 9, 0, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 1, 9, 0, tzinfo=timezone.utc),
        )
        t2 = self.make_ticket(
            id=2,
            title="New Todo",
            status="acknowledged",
            filed_by="him",
            assigned_to="her",
            created_at=datetime.datetime(2023, 1, 5, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 5, 10, 0, tzinfo=timezone.utc),
        )
        t3 = self.make_ticket(
            id=3,
            title="Old In‑Progress",
            status="in_progress",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.datetime(2023, 1, 2, 8, 30, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 2, 8, 30, tzinfo=timezone.utc),
        )
        t4 = self.make_ticket(
            id=4,
            title="New In‑Progress",
            status="in_progress",
            filed_by="him",
            assigned_to="her",
            created_at=datetime.datetime(2023, 1, 6, 11, 15, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 6, 11, 15, tzinfo=timezone.utc),
        )
        session = FakeSession([t1, t2, t3, t4])
        board = household_module.household_board(session, self.today)
        # Verify ordering in todo.
        todo_titles = [t["title"] for t in board["todo"]]
        self.assertEqual(todo_titles, ["Old Todo", "New Todo"], "todo column not ordered by oldest created_at first")
        # Verify ordering in in_progress.
        in_prog_titles = [t["title"] for t in board["in_progress"]]
        self.assertEqual(in_prog_titles, ["Old In‑Progress", "New In‑Progress"], "in_progress column not ordered by oldest created_at first")

    def test_household_board_completed_window_and_order(self):
        """Clause 3 – completed column contains tickets with status done/closed whose updated_at
        falls within the 7‑day window ending on *today* and is ordered newest updated_at first.
        """
        # Ticket outside the window (7 days before today is 2023‑01‑04).
        old_done = self.make_ticket(
            id=1,
            title="Old Done",
            status="done",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.datetime(2022, 12, 20, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 2, 12, 0, tzinfo=timezone.utc),
        )
        # Ticket inside the window.
        recent_done = self.make_ticket(
            id=2,
            title="Recent Done",
            status="done",
            filed_by="him",
            assigned_to="her",
            created_at=datetime.datetime(2023, 1, 5, 9, 0, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 9, 15, 30, tzinfo=timezone.utc),
        )
        # Another inside the window, newer updated_at.
        newest_closed = self.make_ticket(
            id=3,
            title="Newest Closed",
            status="closed",
            filed_by="her",
            assigned_to="him",
            created_at=datetime.datetime(2023, 1, 6, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime.datetime(2023, 1, 10, 8, 0, tzinfo=timezone.utc),
        )
        session = FakeSession([old_done, recent_done, newest_closed])
        board = household_module.household_board(session, self.today)
        completed_titles = [t["title"] for t in board["completed"]]
        # Only the two tickets within the window should appear, newest first.
        self.assertEqual(completed_titles, ["Newest Closed", "Recent Done"], "completed column does not respect 7‑day window or ordering")
        # Ensure no 'group' key is present in completed tickets.
        for ticket_dict in board["completed"]:
            self.assertNotIn("group", ticket_dict)

if __name__ == "__main__":
    unittest.main()
