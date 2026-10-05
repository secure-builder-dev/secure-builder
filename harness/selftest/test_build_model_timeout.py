# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The build driver's test run is bounded: a hung test fails the round instead of stalling the loop."""
import sys
import unittest

from reviewers import build_model
from .helpers import tree


class TestRunBounded(unittest.TestCase):
    def test_a_hung_test_command_is_stopped_and_reported_as_failing(self):
        with tree() as t:
            code, out = build_model.run_tests([sys.executable, "-c", "import time; print('started', flush=True); time.sleep(60)"],
                                              t, timeout=2)
        self.assertNotEqual(code, 0)
        self.assertIn("did not finish within 2s", out)
        self.assertIn("needs its own timeout", out)
        self.assertIn("before shutting the server down", out)

    def test_a_finished_command_reports_its_own_exit_code(self):
        with tree() as t:
            code, out = build_model.run_tests([sys.executable, "-c", "print('ok')"], t)
        self.assertEqual((code, out.strip()), (0, "ok"))


class Guidance(unittest.TestCase):
    def test_repeated_model_mistakes_get_plain_advice(self):
        out = ("ImportError: Failed to import test module: tests.test_geofence" + chr(10) + "ModuleNotFoundError: No module named 'src'" + chr(10)
               + "TypeError: 'HTTPMessage' object is not callable" + chr(10) + "sqlite3.OperationalError: no such table: reports")
        g = build_model.test_guidance(out)
        self.assertIn("Import the code under test inside setUp", g)
        self.assertIn("never r.headers() or e.headers()", g)
        self.assertIn("CREATE TABLE IF NOT EXISTS", g)
        self.assertEqual(build_model.test_guidance("Ran 3 tests" + chr(10) + "OK"), "")

    def test_advice_reaches_the_test_output(self):
        with tree() as t:
            code, out = build_model.run_tests([sys.executable, "-c", "raise TypeError(\"'HTTPMessage' object is not callable\")"], t)
        self.assertIn("ENGINE NOTE: urllib's response and HTTPError headers is an attribute", out)


class NothingRan(unittest.TestCase):
    def test_an_all_skipped_suite_is_a_failed_round(self):
        script = "import unittest, sys" + chr(10) + "class T(unittest.TestCase):" + chr(10) +                  "    @classmethod" + chr(10) + "    def setUpClass(cls): raise unittest.SkipTest('APP_TOKEN unset')" + chr(10) +                  "    def test_a(self): pass" + chr(10) + "unittest.main()"
        with tree() as t:
            (t / "s.py").write_text(script, encoding="utf-8")
            code, out = build_model.run_tests([sys.executable, "s.py"], t)
        self.assertEqual(code, 1)
        self.assertIn("FAIL: the suite ran no test (unittest: Ran 0 tests)", out)
        self.assertIn("must set that value itself", out)

    def test_the_shapes_of_nothing(self):
        f = build_model.suite_ran_nothing
        self.assertIsNone(f("Ran 4 tests in 0.1s" + chr(10) + chr(10) + "OK (skipped=1)"))
        self.assertIn("every test was skipped (3 of 3)", f("Ran 3 tests in 0.1s" + chr(10) + chr(10) + "OK (skipped=3)"))
        self.assertIn("pytest", f("collected 0 items"))
        self.assertIn("pytest", f("==== 4 skipped in 0.12s ===="))
        self.assertIn("mocha", f("  0 passing (3ms)"))
        self.assertIsNone(f("  5 passing (3ms)"))
