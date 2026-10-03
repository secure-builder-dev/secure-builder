# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A handoff names the unit's own item files, not every LETTERS-NUMBER token in its commit messages
(antipode and daynight: control ids, GOV-1 and 'UTF-8' were listed; A-1 and D-1 were missed)."""
import unittest

from engine import handoff
from selftest import helpers


class UnitItems(unittest.TestCase):
    def test_the_items_are_the_tickets_that_name_the_unit(self):
        with helpers.tree() as root:
            helpers.write(root, "tickets/D-1.md", "id: D-1\nunit: DN-1\nstate: in review\n\n# D-1\n")
            helpers.write(root, "tickets/X-9.md", "id: X-9\nunit: OTHER\nstate: open\n\n# X-9\n")
            items, files = handoff.unit_items(root, "DN-1", ["D-1 declare SI-10, SC-18 in the manifest; GOV-1", "fix UTF-8 decode"])
        self.assertEqual((items, files), (["D-1"], ["tickets/D-1.md"]))

    def test_with_no_item_file_the_commit_messages_are_the_fallback(self):
        with helpers.tree() as root:
            items, files = handoff.unit_items(root, "U1", ["NOTES-2 owner check"])
        self.assertEqual((items, files), (["NOTES-2"], []))


if __name__ == "__main__":
    unittest.main()
