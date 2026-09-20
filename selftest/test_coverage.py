# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Coverage measured on the range, thresholds by layer (spec 01 §5.1)."""
import json
import unittest

from engine import coverage
from engine.checks import coverage_range
from engine.config import Config
from engine.outcome import State
from .helpers import commit, git, git_repo, tree, write


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
         "protected_branch": "main"}
    d.update(over)
    return Config(d)


def branch_with_change(t, files):
    git_repo(t)
    write(t, "README.md", "base" + chr(10))
    base = commit(t, "base")
    git(t, "checkout", "-q", "-b", "feature")
    for f, text in files.items():
        write(t, f, text)
    head = commit(t, "change")
    return base, head


class Evaluate(unittest.TestCase):
    def test_threshold_is_on_changed_files_not_project_average(self):
        report = {"src/new.py": 20.0, "src/old.py": 100.0, "src/older.py": 100.0}
        assessed, findings = coverage.evaluate(["src/new.py"], report, coverage.DEFAULT_THRESHOLDS)
        self.assertEqual(assessed, 1)
        self.assertEqual(findings, ["src/new.py: 20.0% covered, threshold 80% for its layer"])

    def test_layer_threshold_higher_where_controls_live(self):
        self.assertEqual(coverage.threshold_for("src/services/auth.py", coverage.DEFAULT_THRESHOLDS), 90.0)
        self.assertEqual(coverage.threshold_for("src/views/page.py", coverage.DEFAULT_THRESHOLDS), 80.0)
        _, findings = coverage.evaluate(["src/services/auth.py"], {"src/services/auth.py": 85.0}, coverage.DEFAULT_THRESHOLDS)
        self.assertEqual(findings, ["src/services/auth.py: 85.0% covered, threshold 90% for its layer"])

    def test_changed_file_absent_from_report_is_a_finding(self):
        _, findings = coverage.evaluate(["src/x.py"], {}, coverage.DEFAULT_THRESHOLDS)
        self.assertEqual(findings, ["src/x.py: changed in range but absent from the coverage report (needs 80%)"])

    def test_tests_and_non_source_ignored(self):
        assessed, findings = coverage.evaluate(["tests/test_x.py", "README.md"], {}, coverage.DEFAULT_THRESHOLDS)
        self.assertEqual((assessed, findings), (0, []))


class Reports(unittest.TestCase):
    def test_reads_three_shapes(self):
        with tree() as t:
            write(t, "a.json", json.dumps({"files": {"src/a.py": {"summary": {"percent_covered": 91.5}}}}))
            write(t, "b.json", json.dumps({"total": {}, "/abs/src/b.js": {"lines": {"pct": 42}}}))
            write(t, "c.json", json.dumps({"files": {"engine/c.py": {"covered": 3, "total": 4}}}))
            self.assertEqual(coverage.read_report(t / "a.json"), {"src/a.py": 91.5})
            self.assertEqual(coverage.read_report(t / "b.json"), {"src/b.js": 42.0})
            self.assertEqual(coverage.read_report(t / "c.json"), {"engine/c.py": 75.0})
            self.assertIsNone(coverage.read_report(t / "missing.json"))


class RangeCheck(unittest.TestCase):
    def test_low_coverage_on_changed_file_is_blocking(self):
        with tree() as t:
            base, head = branch_with_change(t, {"src/new.py": "x = 1" + chr(10)})
            write(t, ".engine/local/coverage.json", json.dumps({"files": {"src/new.py": {"covered": 1, "total": 10}}}))
            o = coverage_range.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["src/new.py: 10.0% covered, threshold 80% for its layer"])

    def test_covered_change_is_clean(self):
        with tree() as t:
            base, head = branch_with_change(t, {"src/new.py": "x = 1" + chr(10)})
            write(t, ".engine/local/coverage.json", json.dumps({"files": {"src/new.py": {"covered": 9, "total": 10}}}))
            o = coverage_range.run(t, cfg())
            self.assertIs(o.state, State.CLEAN)
            self.assertEqual(o.line(), f"[coverage-range] CLEAN: 1 changed source file(s) in {base[:7]}..{head[:7]} meet their layer thresholds")

    def test_missing_report_could_not_run(self):
        with tree() as t:
            branch_with_change(t, {"src/new.py": "x = 1" + chr(10)})
            o = coverage_range.run(t, cfg())
            self.assertIs(o.state, State.COULD_NOT_RUN)
            self.assertIn("no coverage report", o.detail)

    def test_on_protected_branch_nothing_yet(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/a.py", "")
            commit(t)
            self.assertIs(coverage_range.run(t, cfg()).state, State.NOTHING_YET)

    def test_remote_protected_branch_preferred(self):
        with tree() as t:
            base, head = branch_with_change(t, {"src/new.py": "x" + chr(10)})
            git(t, "update-ref", "refs/remotes/origin/main", base)
            git(t, "branch", "-f", "main", head)     # local main drifted to HEAD; remote says base
            write(t, ".engine/local/coverage.json", json.dumps({"files": {"src/new.py": {"covered": 9, "total": 10}}}))
            o = coverage_range.run(t, cfg())
            self.assertIs(o.state, State.CLEAN, o.line())
            self.assertIn(f"{base[:7]}..{head[:7]}", o.line())

    def test_no_protected_branch_could_not_run(self):
        with tree() as t:
            git_repo(t)
            git(t, "checkout", "-q", "-b", "feature")
            write(t, "src/a.py", "")
            commit(t)
            self.assertIs(coverage_range.run(t, cfg()).state, State.COULD_NOT_RUN)


class Collector(unittest.TestCase):
    def test_measures_executed_lines_with_stdlib(self):
        with tree() as t:
            write(t, "engine/__init__.py", "")
            write(t, "engine/m.py", "def f(a):" + chr(10) + "    if a:" + chr(10) + "        return 1" + chr(10) + "    return 2" + chr(10))
            import importlib.util
            spec = importlib.util.spec_from_file_location("fx_m", t / "engine" / "m.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            rep = coverage.collect(t, lambda: mod.f(True))
            self.assertEqual(rep["files"]["engine/m.py"], {"covered": 2, "total": 3})
            self.assertTrue((t / ".engine/local/coverage.json").is_file())
