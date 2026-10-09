# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The single check command (spec 01 REQ-3.1.1–3.1.2) and its summary."""
import json
import pathlib
import unittest

from engine import checks, distribute
from .helpers import cli, cli_sub, commit, find_line, git_repo, tree, write, write_config


FAILING_SUITE = """import unittest
class T(unittest.TestCase):
    def test_bad(self):
        self.assertEqual(1, 2)
"""

SKIPPING_SUITE = """import unittest
class T(unittest.TestCase):
    def test_ok(self):
        pass
    @unittest.skip("needs device")
    def test_dev(self):
        pass
"""


ORDER_SUITE = """import unittest, pathlib
class T(unittest.TestCase):
    def test_a(self):
        pathlib.Path(__file__).resolve().parent.parent.joinpath("order.log").open("a").write("a ")
    def test_b(self):
        pathlib.Path(__file__).resolve().parent.parent.joinpath("order.log").open("a").write("b ")
"""


class Registry(unittest.TestCase):
    def test_every_check_module_is_registered(self):
        here = pathlib.Path(checks.__file__).parent
        on_disk = {p.stem for p in here.glob("*.py") if p.stem != "__init__"}
        registered = set(checks.REGISTRY) - {"config"}
        self.assertEqual(on_disk, registered, "a check exists on disk that no command runs, or vice versa")

    def test_registry_not_empty(self):
        self.assertGreater(len(checks.REGISTRY), 0)


class Check(unittest.TestCase):
    def test_uninitialized_tree_is_red_with_blocking_config_finding(self):
        with tree() as t:
            code, lines = cli(t, "check", "--json")
            self.assertTrue(find_line(lines, "[config] FINDINGS BLOCKING").endswith("no control baseline is defined"))
            self.assertEqual(code, 2, "blocking config finding plus an absent harness suite exits 2")

    def test_initialized_tree_reports_mode_and_version(self):
        with tree() as t:
            write_config(t)
            code, lines = cli(t, "check", "--json")
            find_line(lines, "[config] CLEAN")
            find_line(lines, "mode: local; topology: single; side: local")
            self.assertRegex(find_line(lines, "harness version: "), r"harness version: 0\.\d+\.\d+\S*\+[0-9a-f]{12}$")
            summary = json.loads(find_line(lines, "{"))
            self.assertEqual(summary["mode"], "local")
            self.assertIn("selftest", summary)

    def test_summary_line_counts_separately(self):
        with tree() as t:
            write_config(t)
            _, lines = cli(t, "check")
            self.assertRegex(find_line(lines, "[summary] "),
                             r"^\[summary\] \d+ checks: \d+ applicable, \d+ not applicable, \d+ nothing-yet, \d+ deferred, \d+ failed$")

    def test_selftest_absent_in_foreign_tree_reports_zero_not_pass(self):
        with tree() as t:
            write_config(t)
            code, lines = cli(t, "check")
            find_line(lines, "[selftest] 0 passed, 0 failed, 0 skipped")
            find_line(lines, "[selftest] COULD NOT RUN: zero test cases discovered")
            self.assertEqual(code, 2)


class SelfTestWiring(unittest.TestCase):
    def test_check_command_discovers_this_suite(self):
        from engine.__main__ import discover_selftests
        from .helpers import ROOT
        suite = discover_selftests(ROOT)
        self.assertIsNotNone(suite)
        self.assertGreater(suite.countTestCases(), 40, "the check command would run an empty suite")

    def test_placed_project_runs_the_placed_harness_suite(self):
        """Found by the lifecycle exercise: a project has no selftest/ of its own, so the
        single command must discover the placed copy's suite, not report an absent one."""
        import subprocess, sys
        with tree() as t:
            write_config(t)
            distribute.update(t)
            harness = t / ".engine/harness"
            code = "import sys; from engine.__main__ import discover_selftests; print(discover_selftests(sys.argv[1]).countTestCases())"
            res = subprocess.run([sys.executable, "-c", code, str(t)], cwd=str(harness), capture_output=True, text=True,
                                 env={**__import__("os").environ, "PYTHONPATH": str(harness)})
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertGreater(int(res.stdout.strip()), 40)
            self.assertTrue((harness / "engine/dist/rules/RULES.md").is_file(), "the placed harness is the whole package")

    def test_failing_selftest_is_counted_and_reddens_check(self):
        with tree() as t:
            write_config(t)
            write(t, "selftest/__init__.py", "")
            write(t, "selftest/test_fx.py", FAILING_SUITE)
            distribute.update(t)
            git_repo(t); commit(t)
            code, lines = cli_sub(t, "check")
            find_line(lines, "[selftest] 0 passed, 1 failed, 0 skipped")
            find_line(lines, "[selftest] FAIL: selftest.test_fx.T.test_bad")
            self.assertEqual(code, 1)

    def test_skipped_selftest_is_named_and_counted_separately(self):
        with tree() as t:
            write_config(t)
            write(t, "selftest/__init__.py", "")
            write(t, "selftest/test_fx.py", SKIPPING_SUITE)
            distribute.update(t)
            git_repo(t); commit(t)
            code, lines = cli_sub(t, "check")
            find_line(lines, "[selftest] 1 passed, 0 failed, 1 skipped (skipped: test_dev)")
            self.assertEqual(code, 0)


class OrderIndependence(unittest.TestCase):
    def test_reverse_flag_runs_suite_backwards(self):
        with tree() as t:
            write_config(t)
            write(t, "selftest/__init__.py", "")
            write(t, "selftest/test_fx.py", ORDER_SUITE)
            distribute.update(t)
            git_repo(t); commit(t)
            cli_sub(t, "check")
            self.assertEqual((t / "order.log").read_text().split(), ["a", "b"])
            (t / "order.log").unlink()
            cli_sub(t, "check", "--reverse-tests")
            self.assertEqual((t / "order.log").read_text().split(), ["b", "a"])


class FailureOutput(unittest.TestCase):
    def test_find_line_reports_observed_lines(self):
        with self.assertRaises(AssertionError) as cm:
            find_line(["alpha", "beta"], "[gamma]")
        msg = str(cm.exception)
        self.assertIn("found 0", msg)
        self.assertIn("alpha", msg, "failure output must include the observed value")


class Init(unittest.TestCase):
    def test_init_writes_once_and_refuses_twice(self):
        with tree() as t:
            code, lines = cli(t, "init", "track=android", "mode=disconnected", "app_type=native")
            self.assertEqual(code, 0, lines)
            self.assertIn("track=android tier=IL6 provider=tactical app_type=native", lines[0])
            code, lines = cli(t, "init", "track=web", "mode=local")
            self.assertEqual(code, 1)
            self.assertTrue(lines[0].startswith("init: REFUSED"), lines[0])

    def test_init_requires_explicit_mode(self):
        with tree() as t:
            code, lines = cli(t, "init", "track=web")
            self.assertEqual(code, 2)


class SameCommandEverywhere(unittest.TestCase):
    def test_find_line_matches_line_start_only(self):
        self.assertEqual(find_line(["x [a] y", "[a] z"], "[a]"), "[a] z")
