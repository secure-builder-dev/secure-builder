# © 2026 Casey Houle. All rights reserved.
"""Properties of the build repository itself, as distinct from the harness it builds:
CI runs the single check command (spec 01 REQ-3.1.1). The harness's own suite ships
inside every placed copy and must not depend on this tree's layout.
Run: python tools/build_test.py"""
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent


class Ci(unittest.TestCase):
    def test_ci_runs_the_single_check_command(self):
        lines = (REPO / ".github/workflows/check.yml").read_text(encoding="utf-8").splitlines()
        self.assertIn("      - run: python harness/run.py check", lines)
        self.assertIn("      - run: python work/tools/build_test.py", lines)


if __name__ == "__main__":
    unittest.main()
