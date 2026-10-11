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


class Cwe400Hints(unittest.TestCase):
    def test_a_handler_without_timeout_and_a_single_threaded_server_are_named(self):
        NL = chr(10)
        with tree() as t:
            (t / "src").mkdir()
            (t / "src" / "server.py").write_text(NL.join([
                "import http.server", "from http.server import BaseHTTPRequestHandler, HTTPServer",
                "class Bad(BaseHTTPRequestHandler):", "    def do_GET(self): pass",
                "class Good(http.server.BaseHTTPRequestHandler):", "    timeout = 10",
                "s = HTTPServer(('127.0.0.1', 0), Bad)", "t = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Good)"]) + NL,
                encoding="utf-8")
            hints = build_model.static_hints(t, [t / "src"])
        cwe = [h for h in hints if "CWE-400" in h]
        self.assertEqual(len(cwe), 2, hints)
        self.assertTrue(any("request handler Bad sets no class attribute `timeout`" in h for h in cwe))
        self.assertTrue(any("src/server.py:7: HTTPServer serves one connection at a time" in h for h in cwe))


class StartCheck(unittest.TestCase):
    def test_a_server_that_dies_on_start_is_reported_with_its_output(self):
        with tree() as t:
            msg = build_model.start_check([sys.executable, "-c", "import sys; print('settings.js: bad'); sys.exit(4)"], t, seconds=5)
        self.assertIn("exited with code 4", msg)
        self.assertIn("settings.js: bad", msg)

    def test_a_server_that_keeps_running_passes_and_is_stopped(self):
        with tree() as t:
            self.assertIsNone(build_model.start_check([sys.executable, "-c", "import time; time.sleep(60)"], t, seconds=2))
            self.assertIsNone(build_model.start_check(None, t))
            self.assertIn("could not be run", build_model.start_check(["no-such-program-xyz"], t, seconds=1))


class NoteActedOn(unittest.TestCase):
    """A reviewer note on the tests counts as acted on only when a test function changes, not the imports."""

    def test_an_import_edit_leaves_the_test_bodies_unchanged(self):
        with tree() as t:
            p = t / "tests" / "test_x.py"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("from src import x\n\ndef test_a():\n    assert x.f() == 1\n", encoding="utf-8")
            before = build_model.test_bodies(t, ["tests"])
            p.write_text("import src.x as x\n\ndef test_a():\n    assert x.f() == 1\n", encoding="utf-8")
            self.assertEqual(build_model.test_bodies(t, ["tests"]), before)
            p.write_text("import src.x as x\n\ndef test_a():\n    assert x.f() == 2\n", encoding="utf-8")
            self.assertNotEqual(build_model.test_bodies(t, ["tests"]), before)


class PytestAndVitest(unittest.TestCase):
    """The build driver reads pytest and vitest output, not only unittest's (ticketer: FastAPI + React)."""

    def test_failures_from_both_summaries_are_counted(self):
        out = ("FAILED backend/tests/test_rules.py::test_dashboard - assert 1 == 2\n"
               "========== 2 failed, 5 passed in 1.20s ==========\n"
               " FAIL  tests/App.test.tsx > App > shows three columns\n"
               "      Tests  1 failed | 3 passed (4)\n")
        self.assertEqual(build_model.score(1, out), 3)
        names = build_model.failing_tests(out)
        self.assertIn("backend/tests/test_rules.py::test_dashboard", names)
        self.assertIn("tests/App.test.tsx > App > shows three columns", names)

    def test_a_collection_error_scores_as_uncollectable(self):
        out = "ERROR collecting backend/tests/test_rules.py\n========== 1 error in 0.30s ==========\n"
        self.assertGreaterEqual(build_model.score(1, out), 5_000)
        self.assertEqual(build_model.score(1, "something unparseable"), 10_000)

    def test_typescript_test_names_are_found(self):
        with tree() as t:
            p = t / "frontend" / "tests" / "App.test.tsx"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("it('shows three columns', () => {})\ntest(\"files a ticket\", () => {})\n", encoding="utf-8")
            self.assertEqual(build_model.test_names(t, ["frontend/tests"]), {"shows three columns", "files a ticket"})


class WholeTree(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "the process-tree kill is Windows-specific (taskkill /T)")
    def test_a_hung_child_of_the_test_command_is_stopped_too(self):
        # the launcher (a venv's python.exe, npx.cmd) starts the real test process, which inherits the pipes: killing
        # the launcher alone left the driver waiting on the child for an hour (honey-do DV-1a)
        import time
        child = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
        with tree() as t:
            t0 = time.monotonic()
            code, out = build_model.run_tests([sys.executable, "-c", child], t, timeout=2)
        self.assertEqual(code, 124)
        self.assertLess(time.monotonic() - t0, 30)
        self.assertIn("did not finish within 2s", out)
