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


class ControlWords(unittest.TestCase):
    """antipode ANTI-4: AbortSignal read as cryptography and a comment's 'allows zooming' as authorization."""

    def test_signal_is_not_signing_and_signing_identifiers_still_are(self):
        from engine import controlshape
        self.assertEqual(controlshape.families_in("signal: AbortSignal.timeout(3000)"), [])
        for t in ("def sign_token(key):", "signing_key = 1", "verify the signature"):
            self.assertIn("cryptography", controlshape.families_in(t), t)

    def test_comment_lines_are_not_control_shaped(self):
        from engine import controlshape
        diff = "diff --git a/t.py b/t.py\n+        # map allows zooming to 8\n+    // the policy allows it\n"
        self.assertEqual(controlshape.diff_is_control_shaped(diff), [])
        self.assertIn("authorization", controlshape.diff_is_control_shaped("diff --git a/t.py b/t.py\n+allowlist = {}\n"))


class VendoredDiff(unittest.TestCase):
    def test_a_vendored_file_does_not_make_the_diff_control_shaped(self):
        from engine import controlshape
        vendored = ("diff --git a/src/static/vendor/leaflet/leaflet.js b/src/static/vendor/leaflet/leaflet.js\n"
                    "+++ b/src/static/vendor/leaflet/leaflet.js\n+var token = allowPermission(hash);\n")
        own = "diff --git a/src/auth.py b/src/auth.py\n+++ b/src/auth.py\n+def require_auth(token):\n"
        self.assertEqual(controlshape.diff_is_control_shaped(vendored), [])
        self.assertIn("authentication", controlshape.diff_is_control_shaped(vendored + own))

    def test_the_placed_harness_and_prose_do_not_make_the_diff_control_shaped(self):
        from engine import controlshape
        noise = ("diff --git a/.engine/harness/engine/gate.py b/.engine/harness/engine/gate.py\n+def require_auth(token):\n"
                 "diff --git a/tickets/A-2.md b/tickets/A-2.md\n+the policy allows a hash\n"
                 "diff --git a/.gitattributes b/.gitattributes\n+*.sha binary\n")
        self.assertEqual(controlshape.diff_is_control_shaped(noise), [])


if __name__ == "__main__":
    unittest.main()
