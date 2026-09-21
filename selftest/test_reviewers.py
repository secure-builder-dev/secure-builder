# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The reviewer drivers' hermetic parts: bake-off scoring and re-scoring (no model, no network)."""
import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# the drivers sit beside engine/ in the build tree and at .engine/reviewers/ beside a placed harness
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


if __name__ == "__main__":
    unittest.main()
