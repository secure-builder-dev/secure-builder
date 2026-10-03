# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The tests phase is done only when every clause of the definition of done names an existing test
(antipode A-4: five string checks were offered for an eight-clause definition and it reported success)."""
import contextlib
import importlib.util
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWERS = ROOT / "reviewers" if (ROOT / "reviewers").is_dir() else ROOT.parent / "reviewers"


def load(name):
    spec = importlib.util.spec_from_file_location(name, REVIEWERS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TEST_ONE = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_first_clause(self):\n        self.fail('red')\n"


class ClauseCoverage(unittest.TestCase):
    def setUp(self):
        self.bm = load("build_model")

    def test_clauses_are_the_semicolon_separated_parts(self):
        self.assertEqual(self.bm.split_clauses("a works; b fails ;; c"), ["a works", "b fails", "c"])

    def test_every_case_has_a_test_is_not_a_clause(self):
        self.assertEqual(self.bm.split_clauses("a works; every case has a test"), ["a works"])
        self.assertEqual(self.bm.split_clauses("a works; and every case has its own test."), ["a works"])

    def test_a_clause_is_covered_only_by_an_existing_test(self):
        self.assertEqual(self.bm.uncovered(["a", "b", "c"], {1: "test_a", 2: "test_gone"}, {"test_a"}), [2, 3])

    def test_the_phase_is_not_done_while_a_clause_has_no_test(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "tests").mkdir()
            (root / "tickets").mkdir()
            (root / "tickets" / "X-1.md").write_text(
                "id: X-1\nunit: U\nstate: claimed\ndone_when: the first thing works; the second thing works\n\n# X-1\n", encoding="utf-8")
            answer = {"edits": [{"path": "tests/test_x.py", "search": "", "replace": TEST_ONE}], "notes": "",
                      "coverage": [{"clause": 1, "test": "test_first_clause"}]}
            with mock.patch.object(self.bm, "ask", return_value=(answer, {})), contextlib.redirect_stdout(io.StringIO()) as out:
                code = self.bm.main(["--phase", "tests", "--item", "X-1", "--root", str(root), "--model", "m", "--rounds", "1",
                                     "--test-cmd", f"\"{sys.executable}\" -m unittest discover -s tests -t ."])
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("1 of 2 clause(s) have no test yet: [2]", out.getvalue())


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class DriverRobustness(unittest.TestCase):
    def setUp(self):
        self.bm = load("build_model")

    def test_the_tests_phase_requires_the_coverage_field(self):
        import json
        sent = {}

        def fake(req, timeout=None):
            sent.update(json.loads(req.data.decode("utf-8")))
            return Resp(json.dumps({"message": {"content": "{\"edits\": [], \"notes\": \"\", \"coverage\": []}"}}).encode("utf-8"))
        with mock.patch.object(self.bm.urllib.request, "urlopen", fake):
            self.bm.ask("http://127.0.0.1:1", "m", "s", "u", 1024, require_coverage=True)
        self.assertIn("coverage", sent["format"]["required"])
        self.assertNotIn("coverage", self.bm.SCHEMA["required"], "the build phase does not need it")

    def test_a_server_error_is_a_failed_round_not_the_end(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "tests").mkdir()
            (root / "task.md").write_text("t", encoding="utf-8")
            # the driver's own urllib: the hermetic tier imports no network library itself
            err = self.bm.urllib.error.HTTPError("http://127.0.0.1:1/api/chat", 500, "Internal Server Error", {}, None)
            with mock.patch.object(self.bm, "ask", side_effect=[err, ({"edits": [], "notes": ""}, {})]), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.bm.main(["--phase", "tests", "--task", str(root / "task.md"), "--root", str(root), "--model", "a,b",
                              "--rounds", "2", "--test-cmd", f"\"{sys.executable}\" -c pass"])
        self.assertIn("failed on the server", out.getvalue())
        self.assertIn("round 2 with b", out.getvalue())

    def test_vendored_files_are_never_shown_written_or_rewritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            css = root / "src" / "static" / "vendor" / "lib" / "lib.css"
            css.parent.mkdir(parents=True)
            original = b"a{}\r\nb{}\r\n"
            css.write_bytes(original)
            (root / "src" / "app.py").write_text("X = 1\n", encoding="utf-8")
            self.assertNotIn(css, self.bm.files_under(root, ["src"]))
            written, refused = self.bm.apply_edits(root, [{"path": "src/static/vendor/lib/lib.css", "search": "a{}", "replace": "a{x:1}"}],
                                                   ["src"], set())
            self.assertEqual((written, len(refused)), ([], 1))
            snap = self.bm.snapshot(root, ["src"])
            (root / "src" / "app.py").write_text("X = 2\n", encoding="utf-8")
            self.bm.restore(root, snap, ["src"])
            self.assertEqual(css.read_bytes(), original, "a vendored file keeps its exact bytes")
            self.assertEqual((root / "src" / "app.py").read_text(encoding="utf-8"), "X = 1\n")

    def test_a_repeated_dict_key_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "src" / "s.py").write_text('H = {"A": 1,\n     "B": 2,\n     "A": 3}\nOK = {"A": 1}\n', encoding="utf-8")
            hints = self.bm.static_hints(root, ["src"])
        self.assertEqual(len(hints), 1, hints)
        self.assertIn("src/s.py:3: dict key 'A' is repeated (first at line 1)", hints[0])

    def test_a_test_module_that_cannot_import_scores_worse_than_real_failures(self):
        uncollectable = ("ERROR: test_terminator (unittest.loader._FailedTest.test_terminator)\n"
                         "ImportError: Failed to import test module: test_terminator\n\nFAILED (errors=1)\n")
        ten_real = "FAIL: test_a (tests.t.C.test_a)\n\nFAILED (failures=10)\n"
        self.assertGreater(self.bm.score(1, uncollectable), self.bm.score(1, ten_real))

    def test_a_changed_port_is_not_a_changed_error(self):
        a = "AssertionError: blocked 'http://127.0.0.1:53437/x.css'\n"
        b = "AssertionError: blocked 'http://127.0.0.1:60001/x.css'\n"
        self.assertEqual(self.bm.first_error(a), self.bm.first_error(b))
        self.assertNotEqual(self.bm.first_error(a), self.bm.first_error("AssertionError: 404 != 200\n"))

    def test_failing_test_names_are_read_from_unittest_output(self):
        out = "FAIL: test_a (tests.t.C.test_a)\nERROR: test_b (tests.t.C.test_b)\nok\n"
        self.assertEqual(self.bm.failing_tests(out), {"tests.t.C.test_a", "tests.t.C.test_b"})

    def test_a_tie_that_changes_which_test_fails_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (root / "src" / "m.py").write_text("X = 0\nY = 1\n", encoding="utf-8")
            (root / "tests" / "test_m.py").write_text(
                "import unittest\nfrom src import m\n\n\nclass T(unittest.TestCase):\n"
                "    def test_one(self):\n        self.assertEqual(m.X, 1)\n\n"
                "    def test_two(self):\n        self.assertEqual(m.Y, 1)\n", encoding="utf-8")
            (root / "task.md").write_text("make X one", encoding="utf-8")
            swap = {"edits": [{"path": "src/m.py", "search": "X = 0\nY = 1", "replace": "X = 1\nY = 0"}], "notes": ""}
            idle = {"edits": [], "notes": ""}
            with mock.patch.object(self.bm, "ask", side_effect=[(swap, {}), (idle, {})]), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.bm.main(["--task", str(root / "task.md"), "--root", str(root), "--model", "m", "--rounds", "2",
                              "--test-cmd", f"\"{sys.executable}\" -m unittest discover -s tests -t ."])
            self.assertIn("X = 1", (root / "src" / "m.py").read_text(encoding="utf-8"), out.getvalue())
        self.assertIn("failing: tests.test_m.T.test_two", out.getvalue())

    def test_an_empty_existing_file_can_be_written_with_an_empty_search(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "tests").mkdir()
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests" / "full.py").write_text("X = 1\n", encoding="utf-8")
            written, refused = self.bm.apply_edits(root, [{"path": "tests/__init__.py", "search": "", "replace": "# tests\n"}], ["tests"], set())
            self.assertEqual((written, refused), (["tests/__init__.py"], []))
            written, refused = self.bm.apply_edits(root, [{"path": "tests/full.py", "search": "", "replace": "Y = 2\n"}], ["tests"], set())
            self.assertEqual((written, len(refused)), ([], 1), "a file with content still needs its text quoted")

    def test_a_bare_copyright_line_is_commented_not_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "tests").mkdir()
            written, refused = self.bm.apply_edits(
                root, [{"path": "tests/test_x.py", "search": "", "replace": "© 2026 Casey Houle. All rights reserved.\nX = 1\n"}],
                ["tests"], set())
            self.assertEqual((written, refused), (["tests/test_x.py"], []))
            self.assertTrue((root / "tests" / "test_x.py").read_text(encoding="utf-8").startswith("# © 2026"))

    def test_a_tie_with_the_same_failing_test_but_a_new_error_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (root / "src" / "m.py").write_text("X = 0\n", encoding="utf-8")
            (root / "tests" / "test_m.py").write_text(
                "import unittest\nfrom src import m\n\n\nclass T(unittest.TestCase):\n"
                "    def test_one(self):\n        self.assertEqual(m.X, 1)\n", encoding="utf-8")
            (root / "task.md").write_text("make X one", encoding="utf-8")
            moved = {"edits": [{"path": "src/m.py", "search": "X = 0", "replace": "X = 'two'"}], "notes": ""}
            idle = {"edits": [], "notes": ""}
            with mock.patch.object(self.bm, "ask", side_effect=[(moved, {}), (idle, {})]), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.bm.main(["--task", str(root / "task.md"), "--root", str(root), "--model", "m", "--rounds", "2",
                              "--test-cmd", f"\"{sys.executable}\" -m unittest discover -s tests -t ."])
            self.assertIn("X = 'two'", (root / "src" / "m.py").read_text(encoding="utf-8"), out.getvalue())

    def test_a_function_defined_twice_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "src" / "s.py").write_text("def f():\n    return 1\n\n\ndef g():\n    pass\n\n\ndef f():\n    return 2\n", encoding="utf-8")
            hints = self.bm.static_hints(root, ["src"])
        self.assertEqual(len(hints), 1, hints)
        self.assertIn("src/s.py:9: f is defined again (first at line 1)", hints[0])

    def test_a_search_that_matches_twice_names_its_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "src" / "s.py").write_text("x = 1\ny = 2\nx = 1\n", encoding="utf-8")
            written, refused = self.bm.apply_edits(root, [{"path": "src/s.py", "search": "x = 1", "replace": "x = 3"}], ["src"], set())
        self.assertEqual(written, [])
        self.assertIn("It matches at line 1, line 3", refused[0])

    def test_the_closest_passage_hint_is_capped(self):
        text = "\n".join(f"line {i} " + "x" * 80 for i in range(100))
        hint = self.bm.closest(text, text.replace("line 5 ", "line five "))
        self.assertLessEqual(len(hint), self.bm.HINT_MAX + 40)


if __name__ == "__main__":
    unittest.main()
