# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The standing audit (spec 05 §10) and the negative-fixture check (REQ-2.1, 2.3)."""
import unittest

from engine import audit, checks
from engine.checks import negative_fixtures
from engine.outcome import State
from .helpers import ROOT, cli, find_line, tree, write

CHECK_WITH_LOOP = '''from ..outcome import Outcome
def run(root, cfg):
    hits = [p for p in root.glob("*.cfg")]
    return Outcome.clean("x", "ok")
'''
CHECK_WITH_GUARD = '''from ..outcome import Outcome
def run(root, cfg):
    files = list(root.glob("*.cfg"))
    if not files:
        return Outcome.could_not_run("x", "nothing to scan")
    return Outcome.clean("x", "ok")
'''


def harness_skeleton(t):
    write(t, "engine/__init__.py", "")
    write(t, "engine/checks/__init__.py", "REGISTRY = ['alpha']\n")
    write(t, "engine/checks/alpha.py", CHECK_WITH_GUARD)
    write(t, "selftest/__init__.py", "")


class Q1Dormant(unittest.TestCase):
    def test_test_file_no_path_invokes_is_dormant(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "tools/thing_test.py", "import unittest\n")
            self.assertEqual(audit.q1_dormant_tests(t), ["tools/thing_test.py: no CI workflow, script or hook invokes it"])

    def test_test_file_named_in_ci_is_not_dormant(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "tools/thing_test.py", "import unittest\n")
            write(t, ".github/workflows/check.yml", "run: python tools/thing_test.py\n")
            self.assertEqual(audit.q1_dormant_tests(t), [])

    def test_selftest_files_are_discovered_not_dormant(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "selftest/test_x.py", "import unittest\n")
            self.assertEqual(audit.q1_dormant_tests(t), [])


class Q2NegativeFixtures(unittest.TestCase):
    def test_check_without_failing_test_is_reported(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "selftest/test_alpha.py", "from engine.checks import alpha\nassert alpha.run(1, 2).state is State.CLEAN\n")
            self.assertEqual(audit.q2_checks_without_negative_fixture(t, ["alpha"]),
                             ["check 'alpha': no self-test exercises it against an input that makes it fail"])

    def test_check_with_failing_test_is_proven(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "selftest/test_alpha.py", "from engine.checks import alpha\nassert alpha.run(1, 2).state is State.FINDINGS\n")
            self.assertEqual(audit.q2_checks_without_negative_fixture(t, ["alpha"]), [])

    def test_registered_check_fails_when_a_fixture_is_missing(self):
        with tree() as t:
            harness_skeleton(t)
            o = negative_fixtures.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith("check 'config': no self-test"), o.findings)

    def test_registered_check_could_not_run_without_a_suite(self):
        with tree() as t:
            o = negative_fixtures.run(t, None)
            self.assertIs(o.state, State.COULD_NOT_RUN)

    def test_real_registry_is_fully_proven(self):
        o = negative_fixtures.run(ROOT, None)
        self.assertIs(o.state, State.CLEAN, o.lines())
        self.assertEqual(o.line(), f"[negative-fixtures] CLEAN: all {len(checks.REGISTRY)} registered checks have a self-test that makes them fail")


class Q3EmptyGuard(unittest.TestCase):
    def test_loop_without_guard_flagged(self):
        with tree() as t:
            harness_skeleton(t)
            write(t, "engine/checks/beta.py", CHECK_WITH_LOOP)
            self.assertEqual(audit.q3_loops_without_empty_guard(t),
                             ["engine/checks/beta.py: iterates over a discovered set with no named empty case"])

    def test_loop_with_guard_not_flagged(self):
        with tree() as t:
            harness_skeleton(t)
            self.assertEqual(audit.q3_loops_without_empty_guard(t), [])


class Q4to6Assertions(unittest.TestCase):
    def test_imprecise_assertion_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", "def t(self):\n    self.assertNotEqual(rc, 0)\n")
            self.assertEqual(audit.q4_imprecise_assertions(t),
                             ["selftest/test_x.py:2: asserts a class of values: self.assertNotEqual(rc, 0)"])

    def test_exact_assertion_not_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", "def t(self):\n    self.assertEqual(rc, 1)\n")
            self.assertEqual(audit.q4_imprecise_assertions(t), [])

    def test_whole_output_assertion_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", 'def t(self):\n    self.assertIn("unverified", "\\n".join(lines))\n')
            self.assertEqual(len(audit.q5_whole_output_assertions(t)), 1)

    def test_skip_decorator_flagged_but_not_inside_string_fixture(self):
        with tree() as t:
            write(t, "selftest/test_x.py", 'FX = """\n@unittest.skip("x")\n"""\n@unittest.skip("needs docker")\ndef t(self): pass\n')
            found = audit.q6_environment_dependent_tests(t)
            self.assertEqual(found, ['selftest/test_x.py:4: skips on environment: @unittest.skip("needs docker")'])


class Q7Q8(unittest.TestCase):
    def test_script_without_guard_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", "")
            write(t, "deploy.sh", "#!/bin/sh\nverify\ncommit\n")
            self.assertEqual(audit.q7_sequences_continuing_past_failure(t), ["deploy.sh: no `set -e` and no per-step guard"])
            write(t, "deploy.sh", "#!/bin/sh\nset -e\nverify\ncommit\n")
            self.assertEqual(audit.q7_sequences_continuing_past_failure(t), [])

    def test_tool_without_integration_test_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", "")
            write(t, "engine/scan.py", 'run_tool("trivy", ["image"])\n')
            self.assertEqual(audit.q8_external_tools_only_stubbed(t),
                             ["tool 'trivy': invoked by the harness, exercised by no integration test"])
            write(t, "integration/itest_scan.py", "# runs trivy for real\n")
            self.assertEqual(audit.q8_external_tools_only_stubbed(t), [])


class Command(unittest.TestCase):
    def test_no_tests_is_could_not_run(self):
        with tree() as t:
            code, lines = cli(t, "audit")
            self.assertEqual(code, 2)
            find_line(lines, "[audit] COULD NOT RUN: no test files found")

    def test_audit_reports_and_exits_zero(self):
        code, lines = cli(ROOT, "audit")
        self.assertEqual(code, 0)
        self.assertRegex(find_line(lines, "[audit] 2 checks without"), r": 0 finding\(s\)$")
        find_line(lines, "[audit] 8 external tools")


class Q4Truthy(unittest.TestCase):
    def test_truthy_exit_assertion_flagged(self):
        with tree() as t:
            write(t, "selftest/test_x.py", "def t(self):" + chr(10) + "    self.assertTrue(rc)" + chr(10))
            self.assertEqual(audit.q4_imprecise_assertions(t),
                             ["selftest/test_x.py:2: asserts a class of values: self.assertTrue(rc)"])
