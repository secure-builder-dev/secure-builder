# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Version identity (spec 06 §5)."""
import re
import unittest

import engine


class Version(unittest.TestCase):
    def test_content_derived(self):
        v = engine.version()
        self.assertRegex(v, r"^\d+\.\d+\.\d+\S*\+[0-9a-f]{12}$")
        self.assertEqual(v, engine.version(), "version must be deterministic for an unchanged tree")
