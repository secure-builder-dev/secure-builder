# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The integration tier is separate, and never a pass by default (spec 05 §6.1).
These tests stub the container runtime; they never run one."""
import pathlib
import unittest
from unittest import mock

from engine import integration
from engine.__main__ import SELFTEST_PATTERN
from .helpers import ROOT, cli, find_line, tree, write


class Separation(unittest.TestCase):
    def test_hermetic_tier_discovers_only_selftest(self):
        self.assertEqual(SELFTEST_PATTERN, "test_*.py")
        self.assertEqual(integration.PATTERN, "itest_*.py")
        import re
        imports_tier = re.compile(r"^\s*(from|import)\s+integration")
        for p in (ROOT / "selftest").glob("test_*.py"):
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(imports_tier.match(line), f"{p.name}:{n} imports the integration tier")

    def test_hermetic_tier_imports_no_runtime_or_network(self):
        import re
        bad = re.compile(r"^\s*(import|from)\s+(socket|urllib|docker|requests|http\b)")
        for p in (ROOT / "selftest").glob("*.py"):
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(bad.match(line), f"{p.name}:{n}: {line.strip()}")


class NoRuntime(unittest.TestCase):
    def test_records_not_verified_and_does_not_pass(self):
        with tree() as t:
            with mock.patch.object(integration, "runtime", return_value=None):
                code, lines = integration.run(t)
            self.assertEqual(code, 2)
            find_line(lines, "[integration] COULD NOT RUN: no container runtime")
            rec = (t / integration.RECORD).read_text(encoding="utf-8")
            self.assertRegex(rec, r"- \d{4}-\d{2}-\d{2} · \S+ · integration tier: not verified in this environment \(")
            self.assertNotIn("passed", rec)

    def test_record_is_append_only(self):
        with tree() as t:
            with mock.patch.object(integration, "runtime", return_value=None):
                integration.run(t)
                integration.run(t)
            rec = (t / integration.RECORD).read_text(encoding="utf-8")
            self.assertEqual(rec.count("not verified in this environment"), 2)

    def test_command_exit_and_verdict_line(self):
        with tree() as t:
            with mock.patch.object(integration, "runtime", return_value=None):
                code, lines = cli(t, "integration")
            self.assertEqual(code, 2)
            self.assertEqual(lines[-1], "integration: NOT VERIFIED (exit 2)")


class WithRuntime(unittest.TestCase):
    RT = ("docker", "Docker version 0.0.0-stub")

    def test_empty_tier_is_not_a_pass(self):
        with tree() as t:
            write(t, "integration/__init__.py", "")
            with mock.patch.object(integration, "runtime", return_value=self.RT):
                code, lines = integration.run(t)
            self.assertEqual(code, 2)
            find_line(lines, "[integration] COULD NOT RUN: zero integration tests discovered")
            self.assertIn("not verified in this environment (zero integration tests", (t / integration.RECORD).read_text())

    def test_passing_tier_records_environment(self):
        with tree() as t:
            write(t, "integration/__init__.py", "")
            write(t, "integration/itest_pass.py", "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n")
            with mock.patch.object(integration, "runtime", return_value=self.RT):
                code, lines = integration.run(t)
            self.assertEqual(code, 0, lines)
            find_line(lines, "[integration] 1 passed, 0 failed, 0 skipped")
            rec = (t / integration.RECORD).read_text()
            self.assertRegex(rec, r"integration tier: passed \(environment: .*docker: Docker version 0\.0\.0-stub\)")

    def test_failing_tier_recorded_as_failed(self):
        with tree() as t:
            write(t, "integration/__init__.py", "")
            write(t, "integration/itest_fail.py", "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.fail('x')\n")
            with mock.patch.object(integration, "runtime", return_value=self.RT):
                code, lines = integration.run(t)
            self.assertEqual(code, 1)
            self.assertIn("integration tier: FAILED (1 failed, 0 passed;", (t / integration.RECORD).read_text())
