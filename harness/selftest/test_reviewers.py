# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The reviewer drivers' hermetic parts: bake-off scoring and re-scoring (no model, no network)."""
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# the drivers sit beside engine/ in the build tree and at .engine/harness/reviewers/ beside a placed harness
REVIEWERS = ROOT / "reviewers" if (ROOT / "reviewers").is_dir() else ROOT.parent / "reviewers"


def load(name):
    spec = importlib.util.spec_from_file_location(name, REVIEWERS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VERDICT = {"findings_detail": [
    {"file": "src/app.py", "quote": "return require_auth(request, self.principals, handler)",
     "description": "The delete_note route lacks the ownership check; any authenticated user can delete any note."},
    {"file": "tests/test_notes.py", "quote": "self.assertEqual(status, 401)",
     "description": "No negative test for DELETE by another user."}]}


class Scoring(unittest.TestCase):
    def test_a_truth_with_alternative_fragments_is_found_by_prose_or_quote(self):
        bakeoff = load("bakeoff")
        truths = [("src/app.py", "self.store.delete;delete_note", "delete lacks owner guard"),
                  ("src/app.py", "json.loads;malformed", "malformed json unhandled"),
                  ("tests/test_notes.py", "delete", "no non-owner delete test")]
        found = dict(bakeoff.score(VERDICT, truths))
        self.assertTrue(found["delete lacks owner guard"], "named in prose although a neighbouring line was quoted")
        self.assertFalse(found["malformed json unhandled"])
        self.assertTrue(found["no non-owner delete test"])

    def test_a_single_fragment_truth_still_requires_that_fragment(self):
        bakeoff = load("bakeoff")
        found = dict(bakeoff.score(VERDICT, [("src/app.py", "self.store.delete", "x")]))
        self.assertFalse(found["x"])

    def test_the_file_must_match_even_when_the_fragment_does(self):
        bakeoff = load("bakeoff")
        found = dict(bakeoff.score(VERDICT, [("src/auth.py", "delete_note", "x")]))
        self.assertFalse(found["x"])

    def test_rescore_rewrites_found_from_the_saved_copies_and_runs_nothing(self):
        bakeoff = load("bakeoff")
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            (out / "m-1-rep1.json").write_text(json.dumps(VERDICT), encoding="utf-8")
            (out / "results.json").write_text(json.dumps([{"model": "m:1", "rep": 1, "seconds": 1.0, "valid": True, "verdict": "fail",
                                                            "grounded": 2, "blocking": 2, "ungrounded": 0, "inconsistent": 0, "found": {}}]),
                                              encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                code = bakeoff.rescore(out, [("src/app.py", "delete_note", "guard")])
            self.assertIn("| m:1 | 1/1 | 1/1 |", printed.getvalue())
            self.assertEqual(code, 0)
            rows = json.loads((out / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(rows[0]["found"], {"guard": True})


CHECKLIST = """- [base] B3. Authorization enforcement — Role and scope rules.
- [ELEVATED:informational] ELEVATED1. Validated cryptographic modules only.
"""


class ItemResolution(unittest.TestCase):
    def test_the_item_is_read_from_the_prefixed_field_or_from_the_bare_id(self):
        local_model = load("local_model")
        ids = set(local_model.re.findall(r"^- \[[^\]]*\] (\w+)\.", CHECKLIST, local_model.re.M))
        self.assertEqual(local_model.item_of({"checklist_item": "B3. Authorization enforcement", "id": "F1"}, ids, "checklist_item", "id"), "B3")
        self.assertEqual(local_model.item_of({"checklist_item": "Validated cryptographic modules only.", "id": "ELEVATED1"}, ids,
                                             "checklist_item", "id"), "ELEVATED1",
                         "the informational status of an item cannot be escaped by naming it in prose")
        self.assertEqual(local_model.item_of({"item": "B3. Authorization enforcement", "id": "x"}, ids, "item", "id"), "B3")
        self.assertEqual(local_model.item_of({"checklist_item": "Something else", "id": "F9"}, ids, "checklist_item", "id"), "Something",
                         "an unresolvable item falls back to the leading token, as before")


class Grounding(unittest.TestCase):
    def test_a_quote_grounds_a_finding_only_when_it_has_substance(self):
        local_model = load("local_model")
        self.assertTrue(local_model.substantive('return [n for n in self._notes.values() if term in n["text"]]'))
        self.assertTrue(local_model.substantive("note = self.store.update(note[\"id\"], text)"))
        for trivial in ("]", "}", "return", "pass", "else:", "def f():"):
            self.assertFalse(local_model.substantive(trivial), trivial)


class GovernedInputsAtHead(unittest.TestCase):
    def test_the_manifest_is_read_as_committed_at_the_range_head_not_from_the_working_tree(self):
        # a bake-off replaying an old handoff after a later unit declared a control must not see that control
        import subprocess
        local_model = load("local_model")
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base"], check=True)
            (root / "m.json").write_text('{"controls": ["old"]}', encoding="utf-8")
            subprocess.run(["git", "-C", d, "add", "m.json"], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "head"], check=True)
            head = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            (root / "m.json").write_text('{"controls": ["old", "declared later"]}', encoding="utf-8")
            self.assertEqual(json.loads(local_model.read_at(root, head, "m.json")), {"controls": ["old"]})
            (root / "untracked.md").write_text("working tree only", encoding="utf-8")
            self.assertEqual(local_model.read_at(root, head, "untracked.md"), "working tree only",
                             "a file version control does not hold at head falls back to the working tree")


class BuildEdits(unittest.TestCase):
    """The build driver applies search/replace edits and refuses the ones that would do harm."""

    def setUp(self):
        self.bm = load("build_model")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "a.py").write_text("X = 1\r\nY = 2\r\n", encoding="utf-8", newline="")
        (self.root / "tests" / "test_a.py").write_text("import unittest\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self, edits, readonly=("tests/test_a.py",)):
        return self.bm.apply_edits(self.root, edits, ["src", "tests"], set(readonly))

    def test_an_exact_single_match_is_replaced_and_written_with_lf(self):
        written, refused = self.apply([{"path": "src/a.py", "search": "Y = 2", "replace": "Y = 3"}])
        self.assertEqual((written, refused), (["src/a.py"], []))
        self.assertEqual((self.root / "src" / "a.py").read_bytes(), b"X = 1\nY = 3\n")

    def test_a_new_file_needs_an_empty_search(self):
        self.assertEqual(self.apply([{"path": "src/b.py", "search": "", "replace": "Z = 1\n"}])[0], ["src/b.py"])
        self.assertTrue(self.apply([{"path": "src/c.py", "search": "Z", "replace": "Z = 1\n"}])[1])

    def test_missing_ambiguous_outside_readonly_and_unparsable_edits_are_refused_and_not_written(self):
        before = (self.root / "src" / "a.py").read_bytes()
        cases = [{"path": "src/a.py", "search": "Q = 9", "replace": "Q = 1"},
                 {"path": "src/a.py", "search": " = ", "replace": "="},
                 {"path": ".engine/rules/config.json", "search": "", "replace": "{}"},
                 {"path": "src/../x.py", "search": "", "replace": "1"},
                 {"path": "tests/test_a.py", "search": "import unittest", "replace": "pass"},
                 {"path": "src/a.py", "search": "Y = 2", "replace": "Y = ("}]
        for e in cases:
            written, refused = self.apply([e])
            self.assertEqual((written, len(refused)), ([], 1), e)
        self.assertEqual((self.root / "src" / "a.py").read_bytes(), before)

    def test_a_readonly_test_is_writable_in_the_tests_phase(self):
        self.assertEqual(self.apply([{"path": "tests/test_a.py", "search": "import unittest", "replace": "import unittest\nimport os"}],
                                    readonly=())[0], ["tests/test_a.py"])

    def test_score_counts_failures_and_errors_and_ranks_an_uncollectable_suite_worst(self):
        self.assertEqual(self.bm.score(0, "OK"), 0)
        self.assertEqual(self.bm.score(1, "Ran 9 tests\n\nFAILED (failures=2, errors=1)"), 3)
        self.assertEqual(self.bm.score(1, "SyntaxError: invalid syntax"), 10_000)

    def test_the_request_turns_thinking_off_unless_asked_and_leaves_room_to_answer(self):
        from unittest import mock
        sent = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake(req, timeout=None):
            sent.update(json.loads(req.data.decode("utf-8")))
            return Resp(json.dumps({"message": {"content": "{\"edits\": [], \"notes\": \"\"}"}}).encode("utf-8"))
        with mock.patch.object(self.bm.urllib.request, "urlopen", fake):
            self.bm.ask("http://127.0.0.1:1", "m", "s", "u", 1024)
        self.assertIs(sent["think"], False)
        self.assertGreaterEqual(sent["options"]["num_predict"], 16384)

    def test_the_tests_phase_is_not_done_while_an_edit_was_refused(self):
        from unittest import mock
        (self.root / "tests" / "test_a.py").write_text("import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        pass\n",
                                                      encoding="utf-8")
        answer = {"edits": [{"path": "tests/test_a.py", "search": "        pass", "replace": "        self.fail('red')"},
                            {"path": "tests/test_a.py", "search": "NOT IN THE FILE", "replace": "x"}], "notes": ""}
        (self.root / "task.md").write_text("write the tests", encoding="utf-8")
        with mock.patch.object(self.bm, "ask", return_value=(answer, {})), contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.bm.main(["--phase", "tests", "--task", str(self.root / "task.md"), "--root", str(self.root), "--model", "m",
                                 "--rounds", "1", "--test-cmd", f"\"{sys.executable}\" -m unittest discover -s tests -t ."])
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("REFUSED edit", out.getvalue())

    def test_restore_returns_the_tree_to_a_snapshot(self):
        snap = self.bm.snapshot(self.root, ["src"])
        self.apply([{"path": "src/a.py", "search": "Y = 2", "replace": "Y = 9"}, {"path": "src/new.py", "search": "", "replace": "N = 1\n"}])
        self.bm.restore(self.root, snap, ["src"])
        self.assertFalse((self.root / "src" / "new.py").exists())
        self.assertIn("Y = 2", (self.root / "src" / "a.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
