# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Honest degradation statement (spec 04 §7)."""
import unittest

from engine import config as cfgmod
from engine import degradation
from .helpers import tree, write, write_config


class Statement(unittest.TestCase):
    def test_not_initialized_raises(self):
        with tree() as t:
            with self.assertRaises(cfgmod.ConfigError):
                degradation.statement(t)

    def test_three_categories_present_and_mode_stated(self):
        with tree() as t:
            write_config(t, mode="disconnected")
            s = degradation.statement(t)
            for h in ("## unaffected", "## reduced, quantified", "## not achieved"):
                self.assertIn(h, s)
            self.assertIn("mode: disconnected; topology: single; side: local", s.splitlines()[1])

    def test_single_operator_states_no_separation_of_duties(self):
        with tree() as t:
            write_config(t, operators=1)
            s = degradation.statement(t)
            self.assertIn("- separation of duties: single-operator environment: one person cannot "
                          "independently review their own work", s)
            self.assertLess(s.index("## not achieved"), s.index("- separation of duties:"))

    def test_local_mode_declares_platform_controls_unmet(self):
        with tree() as t:
            write_config(t, mode="local")
            s = degradation.statement(t)
            na = s.split("## not achieved")[1]
            self.assertIn("- protected-branch merge control: no hosting platform", na)
            self.assertIn("a client-side hook reduces accidents and is not a control", na)

    def test_connected_mode_platform_controls_unaffected(self):
        with tree() as t:
            write_config(t, mode="connected", operators=2)
            s = degradation.statement(t)
            self.assertIn("(none)", s.split("## not achieved")[1])

    def test_currency_quantified_when_recorded(self):
        with tree() as t:
            write_config(t, mode="disconnected")
            write(t, ".engine/records/currency-verified", "2000-01-01\n")
            s = degradation.statement(t)
            self.assertRegex(s, r"- catalogue currency: currency not checked in this mode; last verified \d{4,} day\(s\) ago")

    def test_currency_never_verified_says_so(self):
        with tree() as t:
            write_config(t, mode="local")
            self.assertIn("last verified never (no verification recorded)", degradation.statement(t))
