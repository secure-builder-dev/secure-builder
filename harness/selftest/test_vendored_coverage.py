# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""coverage-range does not demand the project's suite cover vendored third-party code (antipode A-2:
leaflet.js under src/static/vendor/ turned the check red)."""
import unittest

from engine.checks import coverage_range


class Vendored(unittest.TestCase):
    def test_files_under_a_vendor_directory_are_vendored(self):
        for p in ("src/static/vendor/leaflet/leaflet.js", "third_party/x.py", "web/node_modules/a/b.js"):
            self.assertTrue(coverage_range.vendored(p), p)

    def test_project_source_is_not(self):
        for p in ("src/app.py", "src/vendors.py", "src/static/index.html", "vendor.py"):
            self.assertFalse(coverage_range.vendored(p), p)


class VendoredDiff(unittest.TestCase):
    def test_a_vendored_file_does_not_make_the_diff_control_shaped(self):
        from engine import controlshape
        vendored = ("diff --git a/src/static/vendor/leaflet/leaflet.js b/src/static/vendor/leaflet/leaflet.js\n"
                    "+++ b/src/static/vendor/leaflet/leaflet.js\n+var token = allowPermission(hash);\n")
        own = "diff --git a/src/auth.py b/src/auth.py\n+++ b/src/auth.py\n+def require_auth(token):\n"
        self.assertEqual(controlshape.diff_is_control_shaped(vendored), [])
        self.assertIn("authentication", controlshape.diff_is_control_shaped(vendored + own))


if __name__ == "__main__":
    unittest.main()
