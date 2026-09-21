# © 2026 Casey Houle. All rights reserved.
"""Negative fixtures for tools/progress.py (spec 07 §2.1a).

Each test constructs a throwaway tree that is complete except for exactly one
defect, runs progress as a subprocess against it, and asserts the specific
clause line progress printed. One positive fixture proves the complete tree
reaches v1.0 — without it, the negatives could be passing because progress
fails on everything.

Run: python tools/progress_test.py
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PROGRESS = HERE / "progress.py"

GOOD_RECEIPT = """REQ:        REQ-1.1
CHECK:      engine/check_one.py
MUTATION:   changed the threshold comparison from > to >= in engine/check_one.py
--- output with the property broken (must show failure) ---
[check-one] FAIL threshold not enforced
exit 1
--- output with the property restored (must show success) ---
[check-one] PASS threshold enforced
exit 0
"""

ENGINE_MAIN = '''import sys, json
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "check":
    print("[selftest] 3 passed, 0 failed, 0 skipped")
    print(json.dumps({"selftest": {"pass": 3, "fail": 0, "skip": 0, "skips": []}}))
    sys.exit(0)
if cmd == "degradation":
    print("mode: local\\nunaffected: all mechanical checks\\nnot achieved: platform merge control")
    sys.exit(0)
sys.exit(2)
'''


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def complete_tree(root):
    """A minimal tree that satisfies every clause of v1.0.md."""
    # four folders: rules/ holds the specs, ledger and v1.0.md; harness/ the package and run.py;
    # records/ the receipts and the lifecycle and release records. Ledger and receipt rows keep
    # naming paths as they were written (engine/..., receipts/...): progress.py resolves them.
    write(root, "rules/specs/01-TEST-SPEC.md", "# Spec\n\n## 1. Section\n\n**REQ-1.1** It MUST.\n")
    write(root, "rules/ledger.tsv",
          "req\tspec\tstage\tstatus\timpl\treceipt\tnote\n"
          "REQ-1.1\t01\t1\tdone\tengine/check_one.py\treceipts/01-REQ-1.1.txt\t\n")
    write(root, "harness/engine/__init__.py", "")
    write(root, "harness/engine/__main__.py", "")
    write(root, "harness/run.py", ENGINE_MAIN)
    write(root, "harness/engine/check_one.py", "def check(): return 0\n")
    write(root, "records/receipts/01-REQ-1.1.txt", GOOD_RECEIPT)
    write(root, "rules/v1.0.md", "# v1.0\n\n## Named skips\n\n(none)\n")
    write(root, "records/LIFECYCLE-EXERCISE.md",
          "# Lifecycle exercise\n\nDate: 2026-10-01\nProject: /tmp/throwaway\n"
          "Range: 0123abc..4567def\nGate-log rows: 3\n")
    write(root, "records/RELEASE-RECORD.md", "integration tier: not verified in this environment\n")


class ProgressFixtures(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="progress-fx-"))
        complete_tree(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_progress(self, *flags):
        res = subprocess.run([sys.executable, str(PROGRESS), "--root", str(self.root), *flags],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines = res.stdout.strip().splitlines()
        return res.returncode, lines, (lines[-1] if lines else "")

    def assert_fails_with(self, needle, *flags):
        rc, lines, verdict = self.run_progress(*flags)
        self.assertNotEqual(rc, 0, f"expected failure; verdict was: {verdict}")
        self.assertTrue(verdict.startswith("progress: NOT v1.0"), f"verdict line was: {verdict}")
        self.assertTrue(any(needle in ln for ln in lines),
                        f"no output line contains {needle!r}; observed:\n" + "\n".join(lines))
        print(f"  asserted: fails with {needle!r}")

    # --- the positive fixture: without it, every negative below is unproven ---

    def test_complete_tree_reaches_v1(self):
        rc, lines, verdict = self.run_progress()
        self.assertEqual(rc, 0, "\n".join(lines))
        self.assertTrue(verdict.startswith("progress: v1.0 REACHED"), verdict)
        self.assertIn("1 requirements done", verdict)
        print("  asserted: complete tree reaches v1.0")

    # --- the empty cases: the vacuous pass sitting on the exit condition ---

    def test_empty_ledger_fails(self):
        write(self.root, "rules/ledger.tsv", "req\tspec\tstage\tstatus\timpl\treceipt\tnote\n")
        self.assert_fails_with("clause 1: ledger.tsv has no rows")

    def test_missing_ledger_fails(self):
        (self.root / "rules/ledger.tsv").unlink()
        self.assert_fails_with("clause 1: ledger.tsv is missing")

    def test_no_requirements_in_specs_fails(self):
        write(self.root, "rules/specs/01-TEST-SPEC.md", "# Spec with nothing numbered\n")
        self.assert_fails_with("clause 1: no requirements found under specs/")

    def test_wrong_header_fails(self):
        write(self.root, "rules/ledger.tsv", "req\tstatus\nREQ-1.1\tdone\n")
        self.assert_fails_with("clause 1: ledger.tsv header must be")

    # --- clause 1: ledger completeness and statuses ---

    def test_requirement_without_row_fails(self):
        write(self.root, "rules/specs/01-TEST-SPEC.md",
              "# Spec\n\n## 1. S\n\n**REQ-1.1** It MUST.\n\n**REQ-1.2** It also MUST.\n")
        self.assert_fails_with("clause 1: 01/REQ-1.2 has no ledger row")

    def test_row_without_requirement_fails(self):
        with (self.root / "rules/ledger.tsv").open("a", encoding="utf-8", newline="\n") as f:
            f.write("REQ-9.9\t01\t1\tna\t-\t-\tinvented\n")
        self.assert_fails_with("clause 1: ledger row 01/REQ-9.9 matches no requirement")

    def test_todo_row_fails(self):
        self._set_row("todo", "-", "-", "")
        self.assert_fails_with("clause 1: 01/REQ-1.1 is still todo")

    def test_doing_row_fails(self):
        self._set_row("doing", "-", "-", "")
        self.assert_fails_with("clause 1: 01/REQ-1.1 is still doing")

    def test_unknown_status_fails(self):
        self._set_row("finished", "-", "-", "")
        self.assert_fails_with("has status 'finished', not one of")

    def test_na_without_reason_fails(self):
        self._set_row("na", "-", "-", "")
        self.assert_fails_with("clause 1: 01/REQ-1.1 is na with no reason")

    def test_defer_without_version_tag_fails(self):
        self._set_row("defer", "-", "-", "later maybe")
        self.assert_fails_with("clause 1: 01/REQ-1.1 is defer with no version tag")

    def test_defer_with_tag_passes(self):
        self._set_row("defer", "-", "-", "v1.1: needs image bundle")
        rc, lines, verdict = self.run_progress()
        self.assertEqual(rc, 0, "\n".join(lines))
        print("  asserted: tagged defer is accepted")

    def test_impl_unknown_fails(self):
        self._set_row("done", "unknown", "receipts/01-REQ-1.1.txt", "")
        self.assert_fails_with("clause 5: 01/REQ-1.1 impl reads 'unknown'")

    # --- clause 2: done rows must be true in the tree ---

    def test_done_with_missing_impl_fails_and_resets(self):
        self._set_row("done", "engine/nope.py", "receipts/01-REQ-1.1.txt", "")
        self.assert_fails_with("marked done but impl engine/nope.py does not exist")
        ledger = (self.root / "rules/ledger.tsv").read_text(encoding="utf-8")
        self.assertIn("\ttodo\t", ledger, "drifted row was not reset to todo")
        self.assertIn("drift:", ledger)
        print("  asserted: drifted row reset to todo with a drift note")

    def test_done_with_missing_impl_no_reset_flag(self):
        self._set_row("done", "engine/nope.py", "receipts/01-REQ-1.1.txt", "")
        self.assert_fails_with("impl engine/nope.py does not exist", "--no-reset")
        self.assertIn("\tdone\t", (self.root / "rules/ledger.tsv").read_text(encoding="utf-8"))

    def test_done_with_no_receipt_fails(self):
        self._set_row("done", "engine/check_one.py", "-", "")
        self.assert_fails_with("marked done but no receipt recorded")

    def test_done_with_absent_receipt_file_fails(self):
        (self.root / "records/receipts/01-REQ-1.1.txt").unlink()
        self.assert_fails_with("receipt receipts/01-REQ-1.1.txt does not exist")

    def test_empty_receipt_fails(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt", "\n\n")
        self.assert_fails_with("receipt receipts/01-REQ-1.1.txt is empty")

    def test_receipt_single_section_fails(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt",
              GOOD_RECEIPT.split("--- output with the property restored")[0])
        self.assert_fails_with("lacks a broken and/or restored section")

    def test_receipt_broken_section_passed_fails(self):
        bad = GOOD_RECEIPT.replace("[check-one] FAIL threshold not enforced\nexit 1",
                                   "[check-one] PASS threshold enforced\nexit 0")
        write(self.root, "records/receipts/01-REQ-1.1.txt", bad)
        self.assert_fails_with("broken section shows no failure")

    def test_receipt_restored_section_still_failing_fails(self):
        bad = GOOD_RECEIPT.replace("[check-one] PASS threshold enforced\nexit 0",
                                   "[check-one] FAIL still broken\nexit 1")
        write(self.root, "records/receipts/01-REQ-1.1.txt", bad)
        self.assert_fails_with("restored section shows no 'exit 0'")

    def test_receipt_for_wrong_requirement_fails(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt", GOOD_RECEIPT.replace("REQ-1.1", "REQ-2.2", 1))
        self.assert_fails_with("names REQ-2.2, row is REQ-1.1")

    def test_receipt_check_path_missing_fails(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt",
              GOOD_RECEIPT.replace("engine/check_one.py", "engine/ghost.py", 1))
        self.assert_fails_with("CHECK path engine/ghost.py does not exist")

    def test_receipt_removal_mutation_fails(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt",
              GOOD_RECEIPT.replace("changed the threshold comparison from > to >= in engine/check_one.py",
                                   "deleted engine/check_one.py"))
        self.assert_fails_with("MUTATION reads as a removal")

    def test_receipt_empty_broken_section_fails(self):
        bad = GOOD_RECEIPT.replace("[check-one] FAIL threshold not enforced\nexit 1\n", "")
        write(self.root, "records/receipts/01-REQ-1.1.txt", bad)
        self.assert_fails_with("broken section is empty")

    # --- clauses 3, 4, 7: the harness itself ---

    def test_red_check_fails(self):
        write(self.root, "harness/run.py", ENGINE_MAIN.replace("sys.exit(0)\nif cmd == \"degradation\"",
                                                                   "sys.exit(1)\nif cmd == \"degradation\""))
        self.assert_fails_with("clause 3: `python harness/run.py check` exited 1")

    def test_selftest_failures_fail(self):
        write(self.root, "harness/run.py",
              ENGINE_MAIN.replace('"fail": 0', '"fail": 2'))
        self.assert_fails_with("clause 4: self-test suite reports 2 failure(s)")

    def test_selftest_zero_passed_fails(self):
        write(self.root, "harness/run.py",
              ENGINE_MAIN.replace('"pass": 3', '"pass": 0'))
        self.assert_fails_with("clause 4: self-test suite passed zero cases")

    def test_unnamed_skip_fails(self):
        write(self.root, "harness/run.py",
              ENGINE_MAIN.replace('"skip": 0, "skips": []', '"skip": 1, "skips": ["needs-docker"]'))
        self.assert_fails_with("clause 4: skip 'needs-docker' is not named in v1.0.md")

    def test_named_skip_passes(self):
        write(self.root, "harness/run.py",
              ENGINE_MAIN.replace('"skip": 0, "skips": []', '"skip": 1, "skips": ["needs-docker"]'))
        write(self.root, "rules/v1.0.md", "# v1.0\n\n## Named skips\n\n- needs-docker\n")
        rc, lines, _ = self.run_progress()
        self.assertEqual(rc, 0, "\n".join(lines))
        print("  asserted: a skip named in v1.0.md is accepted")

    def test_no_json_summary_fails(self):
        write(self.root, "harness/run.py", ENGINE_MAIN.replace("print(json.dumps", "pass  # (json.dumps"))
        self.assert_fails_with("clause 4: check output carried no JSON summary line")

    def test_degradation_failure_fails(self):
        write(self.root, "harness/run.py",
              ENGINE_MAIN.replace('print("mode: local', 'sys.exit(3)\n    print("mode: local'))
        self.assert_fails_with("clause 7: `python harness/run.py degradation` exited 3")

    # --- clauses 6, 8: the human-recorded facts ---

    def test_missing_lifecycle_record_fails(self):
        (self.root / "records/LIFECYCLE-EXERCISE.md").unlink()
        self.assert_fails_with("clause 6: LIFECYCLE-EXERCISE.md does not exist")

    def test_lifecycle_template_fails(self):
        write(self.root, "records/LIFECYCLE-EXERCISE.md", "Date: <date>\nRange: 0123abc..4567def\n")
        self.assert_fails_with("clause 6: LIFECYCLE-EXERCISE.md still contains template placeholders")

    def test_lifecycle_without_range_fails(self):
        write(self.root, "records/LIFECYCLE-EXERCISE.md", "Date: 2026-10-01\nProject: x\n")
        self.assert_fails_with("clause 6: LIFECYCLE-EXERCISE.md names no commit range")

    def test_missing_release_record_fails(self):
        (self.root / "records/RELEASE-RECORD.md").unlink()
        self.assert_fails_with("clause 8: RELEASE-RECORD.md does not exist")

    def test_release_record_claiming_pass_without_environment_fails(self):
        write(self.root, "records/RELEASE-RECORD.md", "integration tier: passed\n")
        self.assert_fails_with("clause 8: RELEASE-RECORD.md records neither")

    def test_release_record_pass_with_environment_passes(self):
        write(self.root, "records/RELEASE-RECORD.md", "Integration tier: passed (environment: linux/docker 27)\n")
        rc, lines, _ = self.run_progress()
        self.assertEqual(rc, 0, "\n".join(lines))
        print("  asserted: passed integration tier with named environment is accepted")

    # --- driver helpers ---

    def test_count_done(self):
        rc, lines, verdict = self.run_progress("--count-done")
        self.assertEqual((rc, verdict), (0, "1"))

    def test_spend_check_without_budget_fails(self):
        rc, lines, verdict = self.run_progress("--spend-check")
        self.assertEqual(rc, 1)
        self.assertIn("budget.txt missing", verdict)

    def test_spend_check_over_budget_fails(self):
        write(self.root, "work/budget.txt", "2\n")
        write(self.root, ".journal/heads", "a\nb\n")
        rc, _, verdict = self.run_progress("--spend-check")
        self.assertEqual(rc, 1, verdict)
        self.assertEqual(verdict, "spend-check: 2 iterations of 2")

    def test_spend_check_under_budget_passes(self):
        write(self.root, "work/budget.txt", "5\n")
        write(self.root, ".journal/heads", "a\nb\n")
        rc, _, verdict = self.run_progress("--spend-check")
        self.assertEqual((rc, verdict), (0, "spend-check: 2 iterations of 5"))

    # --- drift-only (pre-commit hook) ---

    def test_drift_only_tolerates_todo(self):
        self._set_row("todo", "-", "-", "")
        rc, _, verdict = self.run_progress("--drift-only")
        self.assertEqual((rc, verdict), (0, "drift-only: no drift in 0 done row(s)"))

    def test_drift_only_catches_false_done(self):
        self._set_row("done", "engine/nope.py", "receipts/01-REQ-1.1.txt", "")
        rc, lines, verdict = self.run_progress("--drift-only")
        self.assertEqual(rc, 1, verdict)
        self.assertEqual(verdict, "drift-only: 1 row(s) claim done falsely")
        self.assertTrue(any("impl engine/nope.py does not exist" in l for l in lines))

    def test_drift_only_catches_bad_receipt(self):
        write(self.root, "records/receipts/01-REQ-1.1.txt", "REQ: REQ-1.1" + chr(10))
        rc, _, verdict = self.run_progress("--drift-only")
        self.assertEqual((rc, verdict), (1, "drift-only: 1 row(s) claim done falsely"))

    def test_header_text_inside_captured_output_does_not_split_sections(self):
        quoted = GOOD_RECEIPT.replace(
            "[check-one] FAIL threshold not enforced",
            "[check-one] FAIL threshold not enforced (compare '--- output with the property restored' text)")
        write(self.root, "records/receipts/01-REQ-1.1.txt", quoted)
        rc, lines, verdict = self.run_progress()
        self.assertEqual(rc, 0, "\n".join(lines))

    # --- helper ---

    def _set_row(self, status, impl, receipt, note):
        write(self.root, "rules/ledger.tsv",
              "req\tspec\tstage\tstatus\timpl\treceipt\tnote\n"
              f"REQ-1.1\t01\t1\t{status}\t{impl}\t{receipt}\t{note}\n")


if __name__ == "__main__":
    unittest.main(verbosity=1)

