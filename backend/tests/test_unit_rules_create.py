import unittest
from datetime import datetime, timezone
from app.rules import USERS, ticket_to_dict, create_ticket


class TestTicketToDict(unittest.TestCase):
    def test_clause_1_ticket_to_dict(self):
        """Clause 1: ticket_to_dict returns a plain dict with every column."""
        # Mock ticket object
        class MockTicket:
            def __init__(self):
                self.id = 1
                self.title = "Test Title"
                self.details = "Test Details"
                self.priority = "normal"
                self.due = datetime(2023, 1, 1).date()
                self.status = "open"
                self.filed_by = "her"
                self.assigned_to = "him"
                self.created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
                self.updated_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        ticket = MockTicket()
        result = ticket_to_dict(ticket)
        
        # Verify all expected keys are present
        expected_keys = {
            'id', 'title', 'details', 'priority', 'due', 
            'status', 'filed_by', 'assigned_to', 'created_at', 'updated_at'
        }
        self.assertEqual(set(result.keys()), expected_keys)
        
        # Verify due is formatted as YYYY-MM-DD
        self.assertEqual(result['due'], '2023-01-01')
        
        # Verify timestamps are ISO-8601 strings
        self.assertEqual(result['created_at'], '2023-01-01T12:00:00+00:00')
        self.assertEqual(result['updated_at'], '2023-01-01T12:00:00+00:00')


class TestCreateTicket(unittest.TestCase):
    def test_clause_2_filed_by_validation(self):
        """Clause 2: create_ticket raises ValueError when filed_by is not in USERS."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        data = {'title': 'Test', 'details': 'Test details'}
        
        # Test with invalid filed_by
        with self.assertRaises(ValueError):
            create_ticket(session, 'invalid_user', data)

    def test_clause_2_data_keys_validation(self):
        """Clause 2: create_ticket raises ValueError when data holds other keys."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        
        # Test with invalid keys
        invalid_data = {
            'title': 'Test',
            'details': 'Test details',
            'invalid_key': 'invalid_value'
        }
        
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', invalid_data)

    def test_clause_3_title_validation(self):
        """Clause 3: title is required and must be 1-120 chars after stripping."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        
        # Test missing title
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'details': 'Test details'})
        
        # Test non-string title
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 123, 'details': 'Test details'})
        
        # Test title too short after stripping
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': '   ', 'details': 'Test details'})
        
        # Test title too long after stripping
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'a' * 121, 'details': 'Test details'})

    def test_clause_3_details_validation(self):
        """Clause 3: details is optional str of at most 1000 characters."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        
        # Test non-string details
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'Test', 'details': 123})
        
        # Test details too long
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'Test', 'details': 'a' * 1001})

    def test_clause_3_priority_validation(self):
        """Clause 3: priority is optional, one of 'low', 'normal' or 'urgent'."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        
        # Test invalid priority
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'Test', 'priority': 'invalid'})

    def test_clause_3_due_validation(self):
        """Clause 3: due is optional, None or YYYY-MM-DD naming a real date."""
        # Mock session
        class MockSession:
            def add(self, obj): pass
            def commit(self): pass
        
        session = MockSession()
        
        # Test non-string due
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'Test', 'due': 123})
        
        # Test invalid date format
        with self.assertRaises(ValueError):
            create_ticket(session, 'her', {'title': 'Test', 'due': 'invalid-date'})

    def test_clause_4_ticket_creation(self):
        """Clause 4: created ticket has status 'open', assigned to other user, etc."""
        # Mock session
        class MockSession:
            def __init__(self):
                self.added = None
            
            def add(self, obj):
                self.added = obj
            
            def commit(self): pass
        
        session = MockSession()
        data = {
            'title': 'Test Title',
            'details': 'Test Details',
            'priority': 'urgent',
            'due': '2023-12-31'
        }
        
        result = create_ticket(session, 'her', data)
        
        # Verify the ticket was created with correct properties
        self.assertEqual(result['status'], 'open')
        self.assertEqual(result['filed_by'], 'her')
        self.assertEqual(result['assigned_to'], 'him')
        self.assertEqual(result['title'], 'Test Title')
        self.assertEqual(result['details'], 'Test Details')
        self.assertEqual(result['priority'], 'urgent')
        self.assertEqual(result['due'], '2023-12-31')
        
        # Verify timestamps are present and in ISO format
        self.assertIn('created_at', result)
        self.assertIn('updated_at', result)
        self.assertTrue(result['created_at'].endswith('+00:00'))
        self.assertTrue(result['updated_at'].endswith('+00:00'))


if __name__ == '__main__':
    unittest.main()
