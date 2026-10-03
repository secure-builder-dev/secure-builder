# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A started run that will never get a verdict is closed with an 'abandoned' row, and orientation
reads the highest real run, not the last row in the file (antipode ANTI-1 and ANTI-2)."""
import unittest
from unittest import mock

from engine import config as cfgmod, gate, lifecycle
from engine.records import gatelog, schema, templates
from selftest import helpers

A = "a" * 12
B = "b" * 12


class Abandon(unittest.TestCase):
    def test_abandoned_is_a_verdict(self):
        self.assertIn("abandoned", schema.VERDICTS)

    def test_a_started_run_is_closed_once_with_a_reason(self):
        with helpers.tree() as root:
            helpers.write_config(root)
            templates.render_all(root / ".engine" / "records")
            cfg = cfgmod.load(root)
            gatelog.write_started(root, cfg, "U1", "1", f"{A}..{B}", B)
            self.assertEqual(len(gatelog.unmatched_markers(root)), 1)
            line, probs = gate.abandon(root, cfg, "U1", "1", "stale handoff", "Casey Houle")
            self.assertEqual(probs, [])
            self.assertIn("| abandoned |", line)
            self.assertIn("stale handoff", line)
            self.assertEqual(gatelog.unmatched_markers(root), [])
            self.assertTrue(gate.abandon(root, cfg, "U1", "1", "again", "Casey Houle")[1], "a run is closed once")

    def test_no_reason_no_name_or_no_marker_is_refused(self):
        with helpers.tree() as root:
            helpers.write_config(root)
            templates.render_all(root / ".engine" / "records")
            cfg = cfgmod.load(root)
            gatelog.write_started(root, cfg, "U1", "1", f"{A}..{B}", B)
            self.assertTrue(gate.abandon(root, cfg, "U1", "1", "", "Casey Houle")[1])
            self.assertTrue(gate.abandon(root, cfg, "U1", "1", "stale", "")[1])
            self.assertTrue(gate.abandon(root, cfg, "U1", "9", "stale", "Casey Houle")[1])


class LatestRun(unittest.TestCase):
    def test_orient_reads_the_highest_run_and_ignores_abandoned_rows(self):
        rows = [{"unit": "U9", "run": "2", "verdict": "pass", "findings": "0"},
                {"unit": "U9", "run": "1", "verdict": "fail", "findings": "1: F-1"},
                {"unit": "U9", "run": "3", "verdict": "abandoned", "findings": "1: ABANDONED - stale"}]
        with helpers.tree() as root:
            helpers.write(root, "plans/units/U9.md", "id: U9\nstate: in review\n\n# U9\n")
            with mock.patch.object(lifecycle.gitutil, "is_repo", return_value=True), \
                    mock.patch.object(lifecycle.gitutil, "current_branch", return_value="unit/U9"), \
                    mock.patch.object(lifecycle.gitutil, "head", return_value=B), \
                    mock.patch.object(lifecycle.gitutil, "rev", return_value=""), \
                    mock.patch.object(lifecycle.gatelog, "series", return_value=(rows, [])):
                lines = lifecycle.orient(root, None)
        text = "\n".join(lines)
        self.assertIn("last gate: run 2 pass", text)
        self.assertIn("await the gate verdict and the human merge", text)


if __name__ == "__main__":
    unittest.main()
