import unittest
import datetime
from app import rules
from app.models import Ticket, TicketEvent

class TestEditTicket(unittest.TestCase):
    def setUp(self):
        # db fixture is provided by conftest; we obtain a fresh session per test via self.db
        from tests.conftest import db as db_fixture
        self.db = db_fixture()
        # Ensure a clean session for each test
        self.session = self.db
        # Create a baseline ticket filed by 'her'
        self.ticket = rules.create_ticket(self.session, "her", {"title": "Initial", "details": "", "priority": "normal"})
        self.ticket_id = self.ticket["id"]

    def tearDown(self):
        self.session.close()

    # Clause 1: raise errors in the correct order
    def test_edit_ticket_raises_in_order(self):
        # 1a) LookupError when ticket does not exist
        with self.assertRaises(LookupError):
            rules.edit_ticket(self.session, 9999, "her", {"title": "New"})

        # 1b) LookupError when user is not a party
        with self.assertRaises(LookupError):
            rules.edit_ticket(self.session, self.ticket_id, "other", {"title": "New"})

        # 1c) ValueError when data is not a dict
        with self.assertRaises(ValueError):
            rules.edit_ticket(self.session, self.ticket_id, "her", "not a dict")

        # 1d) ValueError when data is empty dict
        with self.assertRaises(ValueError):
            rules.edit_ticket(self.session, self.ticket_id, "her", {})

        # 1e) ValueError when data contains an unexpected key
        with self.assertRaises(ValueError):
            rules.edit_ticket(self.session, self.ticket_id, "her", {"foo": "bar"})

        # 1f) ValueError when a value would be rejected by create_ticket (title too long)
        long_title = "x" * 121
        with self.assertRaises(ValueError):
            rules.edit_ticket(self.session, self.ticket_id, "her", {"title": long_title})

        # 1g) PermissionError when user is not the filer (assignee tries to edit)
        # The ticket is assigned to "him" (the other user)
        with self.assertRaises(PermissionError):
            rules.edit_ticket(self.session, self.ticket_id, "him", {"title": "New"})

        # 1h) NotEditable when status is not open or acknowledged
        # Move ticket to in_progress first (allowed transition by assignee)
        rules.change_status(self.session, self.ticket_id, "him", "acknowledged")
        rules.change_status(self.session, self.ticket_id, "him", "in_progress")
        with self.assertRaises(rules.NotEditable):
            rules.edit_ticket(self.session, self.ticket_id, "her", {"title": "New"})

    # Clause 2: NotEditable subclass checks
    def test_noteditable_subclass(self):
        self.assertTrue(issubclass(rules.NotEditable, Exception))
        self.assertFalse(issubclass(rules.NotEditable, ValueError))
        self.assertFalse(issubclass(rules.NotEditable, PermissionError))

    # Clause 3: successful edit behavior
    def test_successful_edit_changes_fields_and_records_event(self):
        original = self.session.get(Ticket, self.ticket_id)
        original_updated = original.updated_at
        # Perform edit with title (needs stripping) and details
        result = rules.edit_ticket(
            self.session,
            self.ticket_id,
            "her",
            {"title": "  New Title  ", "details": "New details"},
        )
        # Verify returned dict reflects changes
        self.assertEqual(result["title"], "New Title")
        self.assertEqual(result["details"], "New details")
        # Verify other fields unchanged
        self.assertEqual(result["priority"], original.priority)
        self.assertEqual(result["due"], original.due.isoformat() if original.due else None)
        # Verify updated_at changed
        self.assertNotEqual(result["updated_at"], original_updated.isoformat())
        # Verify database reflects changes
        refreshed = self.session.get(Ticket, self.ticket_id)
        self.assertEqual(refreshed.title, "New Title")
        self.assertEqual(refreshed.details, "New details")
        # Verify an 'edited' event was recorded
        events = (
            self.session.query(TicketEvent)
            .filter(TicketEvent.ticket_id == self.ticket_id, TicketEvent.kind == "edited")
            .all()
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev.actor, "her")
        self.assertIsNone(ev.from_status)
        self.assertIsNone(ev.to_status)
        # Ensure the transaction was committed (event persisted)
        self.session.commit()

    # Clause 4: failed edit makes no changes and records nothing
    def test_failed_edit_no_change_no_event(self):
        # Count events before
        before_events = (
            self.session.query(TicketEvent)
            .filter(TicketEvent.ticket_id == self.ticket_id)
            .count()
        )
        # Attempt edit with invalid title (too long)
        long_title = "x" * 121
        with self.assertRaises(ValueError):
            rules.edit_ticket(self.session, self.ticket_id, "her", {"title": long_title})
        # Verify ticket unchanged
        ticket = self.session.get(Ticket, self.ticket_id)
        self.assertEqual(ticket.title, "Initial")
        # Verify no new events recorded
        after_events = (
            self.session.query(TicketEvent)
            .filter(TicketEvent.ticket_id == self.ticket_id)
            .count()
        )
        self.assertEqual(before_events, after_events)

if __name__ == "__main__":
    unittest.main()
