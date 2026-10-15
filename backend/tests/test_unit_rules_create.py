import unittest
from datetime import datetime, timezone
from app.rules import USERS, ticket_to_dict, create_ticket


class TestTicketToDict(unittest.TestCase):
    def test_clause_1_ticket_to_dict(self):
        """Clause 1: ticket_to_dict returns a plain dict with every column."""
        # This test will fail until ticket_to_dict is implemented
        self.fail("ticket_to_dict not yet implemented")


class TestCreateTicket(unittest.TestCase):
    def test_clause_2_filed_by_validation(self):
        """Clause 2: create_ticket raises ValueError when filed_by is not in USERS."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_2_data_keys_validation(self):
        """Clause 2: create_ticket raises ValueError when data holds other keys."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_3_title_validation(self):
        """Clause 3: title is required and must be 1-120 chars after stripping."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_3_details_validation(self):
        """Clause 3: details is optional str of at most 1000 characters."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_3_priority_validation(self):
        """Clause 3: priority is optional, one of 'low', 'normal' or 'urgent'."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_3_due_validation(self):
        """Clause 3: due is optional, None or YYYY-MM-DD naming a real date."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")

    def test_clause_4_ticket_creation(self):
        """Clause 4: created ticket has status 'open', assigned to other user, etc."""
        # This test will fail until create_ticket is implemented
        self.fail("create_ticket not yet implemented")


if __name__ == '__main__':
    unittest.main()
