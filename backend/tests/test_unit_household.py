import unittest
from datetime import datetime, date, timezone, timedelta
from app.household import household_board
from app.models import Ticket
from app.rules import ticket_to_dict


class TestHouseholdBoard(unittest.TestCase):
    def test_clause_1(self):
        """Clause 1: household_board returns dict with todo, in_progress, completed."""
        # This test will fail until household_board is implemented
        self.fail("household_board not yet implemented")

    def test_clause_2_todo_order(self):
        """Clause 2: todo holds open/acknowledged tickets ordered by created_at oldest first."""
        # This test will fail until household_board is implemented
        self.fail("household_board not yet implemented")

    def test_clause_2_in_progress_order(self):
        """Clause 2: in_progress holds in_progress tickets ordered by created_at oldest first."""
        # This test will fail until household_board is implemented
        self.fail("household_board not yet implemented")

    def test_clause_3_completed_order(self):
        """Clause 3: completed holds done/closed tickets with updated_at in last 7 days, newest first."""
        # This test will fail until household_board is implemented
        self.fail("household_board not yet implemented")


if __name__ == '__main__':
    unittest.main()