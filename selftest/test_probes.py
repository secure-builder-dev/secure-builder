# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Standing-state probes, completeness probe, coverage inventory, adoption dispositions,
ungated inbound (spec 01 §9, §7.5; spec 02 §7–8; spec 06 REQ-7.3; spec 04 §10.3)."""
import json
import unittest

from engine import distribute, manifest, probes
from engine.checks import assessed_boundary, manifest_completeness
from engine.config import Config
from engine.outcome import State
from engine.records import findings, gatelog, table, templates
from .helpers import commit, git, git_repo, tree, write, write_config

NL = chr(10)


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
         "protected_branch": "main", "side": "low", "timezone": "UTC", "test_command": ["pytest"], "lint_command": ["ruff", "."]}
    d.update(over)
    return Config(d)


def project(t, ci=True):
    write_config(t, protected_branch="main", side="low", timezone="UTC", test_command=["pytest"], lint_command=["ruff", "."])
    templates.render_all(t / ".engine/records")
    write(t, manifest.FILE, json.dumps({"scope_statement": manifest.SCOPE_STATEMENT, "controls": []}))
    if ci:
        write(t, ".github/workflows/ci.yml", "run: pytest" + NL + "run: ruff ." + NL)
    git_repo(t)
    write(t, "src/app.py", "def used(): pass" + NL + "def unused_helper(): pass" + NL + "used()" + NL)
    return commit(t, "base")


class Snapshot(unittest.TestCase):
    def test_measurement_set_and_no_suite_run(self):
        with tree() as t:
            project(t)
            m = probes.measure(t, cfg(), test_result="12 passed")
            for k in ("ci_runs_tests", "ci_runs_lint", "deployment_artifact_count", "test_result_counts",
                      "control_manifest_result", "exported_symbols_without_call_site"):
                self.assertIn(k, m)
            self.assertEqual((m["ci_runs_tests"], m["ci_runs_lint"], m["test_result_counts"]), (True, True, "12 passed"))
            self.assertEqual(m["exported_symbols_without_call_site"], 1)
            import inspect
            self.assertNotIn("run_tool", inspect.getsource(probes.measure), "the probe never runs the suite; the result is passed in")

    def test_snapshot_keyed_by_commit_and_idempotent(self):
        with tree() as t:
            head = project(t)
            cur, prev, p = probes.snapshot(t, cfg(), head, "1 passed")
            self.assertIsNone(prev)
            self.assertEqual(p.name, f"{head}.json")
            cur2, prev2, p2 = probes.snapshot(t, cfg(), head, "different")
            self.assertEqual(cur, cur2, "re-running at the same commit is idempotent")
            self.assertEqual(len(list((t / probes.SNAPSHOT_DIR).glob("*.json"))), 1)

    def test_first_probe_is_nothing_yet_then_unchanged_is_clean(self):
        with tree() as t:
            h1 = project(t)
            self.assertIs(probes.run_probe(t, cfg(), h1).state, State.NOTHING_YET)
            write(t, "README.md", "x" + NL); h2 = commit(t, "docs")
            o = probes.run_probe(t, cfg(), h2)
            self.assertIs(o.state, State.CLEAN, o.line())


class PerGate(unittest.TestCase):
    def test_gate_prepare_captures_a_snapshot_for_head(self):
        from engine import gate
        from .test_gate import feature, project as gate_project
        with tree() as t:
            base = gate_project(t)
            head = feature(t, files={"docs/x.md": "hi" + NL})
            write(t, ".engine/local/coverage.json", json.dumps({"files": {}}))
            gate.prepare(t, Config({"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
                                    "protected_branch": "main", "side": "low", "timezone": "UTC", "test_command": ["python", "-c", "pass"]}),
                         "epic-7", "1", base, head)
            self.assertTrue((t / probes.SNAPSHOT_DIR / f"{head}.json").is_file(), "a snapshot is captured per gate")


class Deltas(unittest.TestCase):
    def test_undispositioned_delta_opens_ticket_and_does_not_block(self):
        with tree() as t:
            h1 = project(t)
            probes.run_probe(t, cfg(), h1)
            write(t, "Dockerfile", "FROM scratch" + NL); h2 = commit(t, "add deploy artifact")
            o = probes.run_probe(t, cfg(), h2)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertTrue(o.findings[0].startswith("deployment_artifact_count: 0 -> 1 — undispositioned; ticket DELTA-deployment_artifact_count-"), o.findings)
            self.assertTrue((t / "tickets" / f"DELTA-deployment_artifact_count-{h2[:12]}.md").is_file())
            rows, _, _ = table.read(t, probes.DELTAS, "standing-state-deltas")
            self.assertEqual((rows[0]["measurement"], rows[0]["previous"], rows[0]["current"]), ("deployment_artifact_count", "0", "1"))
            self.assertTrue(rows[0]["disposition"].startswith("ticket DELTA-deployment_artifact_count-"), "every recorded delta carries its disposition")

    def test_dispositioned_delta_is_clean(self):
        with tree() as t:
            h1 = project(t)
            probes.run_probe(t, cfg(), h1)
            write(t, "Dockerfile", "FROM scratch" + NL); h2 = commit(t, "add deploy artifact")
            probes.record_delta(t, cfg(), h2, "deployment_artifact_count", 0, 1, "expected: first container image, finding F-3")
            o = probes.run_probe(t, cfg(), h2)
            self.assertIs(o.state, State.CLEAN, o.line())

    def test_control_decay_blocks_even_when_dispositioned(self):
        with tree() as t:
            h1 = project(t)
            probes.run_probe(t, cfg(), h1)
            write(t, ".github/workflows/ci.yml", "run: echo skip" + NL); h2 = commit(t, "ci stops testing")
            probes.record_delta(t, cfg(), h2, "ci_runs_tests", True, False, "we know")
            o = probes.run_probe(t, cfg(), h2)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(any(f.startswith("ci_runs_tests: True -> False — control decay blocks even when dispositioned (we know)") for f in o.findings), o.findings)

    def test_manifest_regression_is_decay(self):
        self.assertTrue(probes.is_decay("control_manifest_result", "resolved", "failed"))
        self.assertTrue(probes.is_decay("required_artifacts_present", True, False))
        self.assertFalse(probes.is_decay("deployment_artifact_count", 1, 2))
        self.assertFalse(probes.is_decay("ci_runs_tests", False, True))


class Completeness(unittest.TestCase):
    def test_undeclared_control_listed_and_dispositions_retained(self):
        with tree() as t:
            project(t)
            write(t, "src/auth.py", "def require_auth(r): pass" + NL + "def redact_pii(x): pass" + NL)
            git(t, "add", "-A")
            o = manifest_completeness.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking, "the probe never blocks")
            self.assertEqual(sorted(f.split(" ")[1] for f in o.findings), ["redact_pii", "require_auth"])
            p = t / probes.UNDECLARED
            p.write_text(p.read_text(encoding="utf-8").replace("| src/auth.py | redact_pii | redaction |  |  |",
                                                               "| src/auth.py | redact_pii | redaction | not-a-control | log formatter |"), encoding="utf-8")
            o = manifest_completeness.run(t, cfg())
            self.assertEqual([f.split(" ")[1] for f in o.findings], ["require_auth"])
            self.assertIn("| src/auth.py | redact_pii | redaction | not-a-control | log formatter |", (t / probes.UNDECLARED).read_text(encoding="utf-8"))

    def test_declared_symbol_not_listed(self):
        with tree() as t:
            project(t)
            write(t, "src/auth.py", "def require_auth(r): pass" + NL)
            write(t, manifest.FILE, json.dumps({"scope_statement": manifest.SCOPE_STATEMENT, "controls": [
                {"id": "C-1", "description": "d", "location": {"file": "src/auth.py", "symbol": "require_auth"}, "test_pattern": "t", "status": "system-specific"}]}))
            git(t, "add", "-A")
            self.assertEqual(probes.undeclared_controls(t), [])

    def test_uses_the_same_detection_as_the_trigger(self):
        import inspect
        self.assertIn("controlshape.control_symbols", inspect.getsource(probes.undeclared_controls))


class Inventory(unittest.TestCase):
    def gated_project(self, t):
        base = project(t)
        git(t, "update-ref", "refs/remotes/origin/main", base)
        write(t, "src/new.py", "x = 1" + NL); head = commit(t, "feature")
        gatelog.append(t, cfg(), unit="e", range=f"{base[:12]}..{head[:12]}", run="1", verdict="pass", reviewer="r",
                       reviewer_class="automated", attested_by="Casey")
        return base, head

    def test_three_states_from_gate_log_evidence(self):
        with tree() as t:
            base, head = self.gated_project(t)
            write(t, probes.RECEIVED, json.dumps({"drops": [{"commit": "abc", "files": ["src/app.py"], "records_transferred": False}]}))
            rows, counts = probes.write_inventory(t, cfg())
            states = {f: s for f, s, _ in rows}
            self.assertEqual(states["src/new.py"], "assessed")
            self.assertEqual(states["src/app.py"], "assessed elsewhere, evidence not available")
            self.assertEqual(counts, {"assessed": 1, "never": 0, "elsewhere": 1})
            text = (t / probes.INVENTORY).read_text(encoding="utf-8")
            self.assertIn("it is not a clean bill of health", text)
            self.assertIn("assessed elsewhere, evidence not available: 1 (50%)", text)

    def test_never_assessed_without_gate_rows(self):
        with tree() as t:
            project(t)
            rows, counts = probes.write_inventory(t, cfg())
            self.assertEqual(counts, {"assessed": 0, "never": 1, "elsewhere": 0})

    def test_failed_or_superseded_rows_do_not_count_as_assessment(self):
        with tree() as t:
            base = project(t)
            write(t, "src/new.py", "x" + NL); head = commit(t, "f")
            gatelog.append(t, cfg(), unit="e", range=f"{base[:12]}..{head[:12]}", run="1", verdict="fail", reviewer="r",
                           reviewer_class="automated", attested_by="Casey", findings="1: F-1")
            rows, counts = probes.write_inventory(t, cfg())
            self.assertEqual(counts["assessed"], 0)


class Adoption(unittest.TestCase):
    def test_every_row_needs_a_disposition(self):
        with tree() as t:
            project(t)
            write(t, probes.ADOPTION, "| file | disposition | reason |" + NL + "|---|---|---|" + NL +
                  "| src/a.py |  |  |" + NL + "| src/b.py | accepted |  |" + NL + "| src/c.py | reviewed |  |" + NL)
            probs, n = probes.adoption_problems(t)
            self.assertEqual(n, 3)
            self.assertEqual(probs, ["src/a.py: no disposition (reviewed, accepted with a reason, or scheduled)", "src/b.py: accepted without a written reason"])
            o = assessed_boundary.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertTrue(o.findings[0].startswith("adoption inventory: src/a.py"))


class Ungated(unittest.TestCase):
    def test_commit_on_protected_branch_outside_any_gate_is_reported_unless_recorded(self):
        with tree() as t:
            base = project(t)
            write(t, "src/new.py", "x" + NL); head = commit(t, "gated")
            gatelog.append(t, cfg(), unit="e", range=f"{base[:12]}..{head[:12]}", run="1", verdict="pass", reviewer="r",
                           reviewer_class="automated", attested_by="Casey")
            write(t, "src/hot.py", "y" + NL); hot = commit(t, "hotfix straight to main")
            git(t, "update-ref", "refs/remotes/origin/main", hot)
            un = probes.ungated_inbound(t, cfg())
            self.assertEqual(un, [hot])
            o = assessed_boundary.run(t, cfg())
            self.assertTrue(any(f"ungated inbound: commit {hot[:12]}" in f for f in o.findings), o.findings)
            findings.add_risk(t, cfg(), id="R-9", risk=f"ungated merge {hot[:12]} accepted under incident 4", attack_path="unreviewed code on main",
                              compensating_control="post-hoc review", proof="tests/test_hot.py runs in CI", re_review_trigger="release",
                              owner="casey", review_by="2027-01-01", decided_by="Casey", status="accepted")
            self.assertEqual(probes.ungated_inbound(t, cfg()), [])

    def test_no_gate_rows_yet_is_none(self):
        with tree() as t:
            project(t)
            git(t, "update-ref", "refs/remotes/origin/main", commit(t, "c"))
            self.assertIsNone(probes.ungated_inbound(t, cfg()))
