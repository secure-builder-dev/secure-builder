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


if __name__ == "__main__":
    unittest.main()
