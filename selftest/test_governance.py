# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The governance protocol (spec 01 §11; spec 02 §5)."""
import json
import unittest

from engine import distribute, gate, governance
from engine.config import Config
from engine.outcome import State
from engine.records import changelog, gatelog
from .helpers import cli, commit, find_line, git, git_repo, tree, write, write_config

NL = chr(10)


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
         "protected_branch": "main", "side": "low", "timezone": "UTC", "test_command": ["python", "-c", "pass"]}
    d.update(over)
    return Config(d)


def project(t):
    write_config(t, protected_branch="main", side="low", timezone="UTC", test_command=["python", "-c", "pass"])
    distribute.update(t)
    git_repo(t)
    write(t, "src/app.py", "app = 1" + NL)
    base = commit(t, "base")
    git(t, "update-ref", "refs/remotes/origin/main", base)
    git(t, "checkout", "-q", "-b", "epic-9")
    return base


class Set(unittest.TestCase):
    def test_governed_set_includes_rulebook_definitions_manifest_config_and_itself(self):
        g = governance.governed_set(None, cfg())
        for p in ("AGENTS.md", ".engine/rules/", ".engine/rules/agents/", ".engine/rules/control-manifest.json", ".engine/rules/config.json", governance.ZONES_FILE):
            self.assertIn(p, g)
        self.assertTrue(governance.is_governed(".engine/rules/agents/security-gate.md", g))
        self.assertFalse(governance.is_governed("src/app.py", g))

    def test_zones_are_an_explicit_allowlist(self):
        with tree() as t:
            distribute.update(t)
            zs = governance.zones(t)
            self.assertEqual(zs, [{"file": "AGENTS.md", "section": "## Project rules"}])
            self.assertFalse(governance.in_zone("AGENTS.md", "## Precedence", zs))


class Automation(unittest.TestCase):
    def test_append_grounded_entry_only_in_zone_with_source(self):
        with tree() as t:
            distribute.update(t)
            before = (t / "AGENTS.md").read_text(encoding="utf-8")
            entry = governance.append_grounded(t, "AGENTS.md", "## Project rules", "Every record-scoped query filters by owner.", "[finding: F-7]")
            after = (t / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(after.splitlines(), before.splitlines() + [entry] if before.endswith("\n") else before.splitlines() + [entry])
            self.assertTrue(entry.endswith("[finding: F-7]"))
            with self.assertRaises(PermissionError) as cm:
                governance.append_grounded(t, "AGENTS.md", "## Precedence", "x", "[finding: F-8]")
            self.assertIn("not an agent-editable zone", str(cm.exception))
            with self.assertRaises(PermissionError) as cm:
                governance.append_grounded(t, "AGENTS.md", "## Project rules", "y", "because I said so")
            self.assertIn("must cite an external, already-approved source", str(cm.exception))

    def test_append_never_rewrites_or_deletes(self):
        with tree() as t:
            distribute.update(t)
            governance.append_grounded(t, "AGENTS.md", "## Project rules", "first", "[decision: D-1]")
            governance.append_grounded(t, "AGENTS.md", "## Project rules", "second", "[decision: D-2]")
            lines = (t / "AGENTS.md").read_text(encoding="utf-8").splitlines()
            i = lines.index("- first [decision: D-1]")
            self.assertEqual(lines[i + 1], "- second [decision: D-2]")
            self.assertIn("## Precedence", lines)

    def test_disposition_command(self):
        with tree() as t:
            write_config(t); distribute.update(t)
            code, lines = cli(t, "disposition", "checklist-line", "text=No route without a negative test.", "source=[finding: F-2]")
            self.assertEqual(code, 0, lines)
            self.assertIn("- No route without a negative test. [finding: F-2]", (t / "AGENTS.md").read_text(encoding="utf-8").splitlines())


class Changelog(unittest.TestCase):
    def test_record_writes_row_before_commit_with_what_was_shown(self):
        with tree() as t:
            project(t)
            write(t, "AGENTS.md", (t / "AGENTS.md").read_text(encoding="utf-8") + "- new invariant" + NL)
            git(t, "add", "AGENTS.md")
            code, lines = cli(t, "governance", "propose")
            self.assertEqual(code, 0)
            find_line(lines, "governance: the literal text being changed — shown in the request itself, never behind a detail:")
            self.assertTrue(any(l.startswith("+- new invariant") for l in lines), lines)
            code, lines = cli(t, "governance", "record", "change_id=G-1", "file_section=AGENTS.md ## Project rules",
                              "grounding=decision D-3", "approved_by=Casey Houle")
            self.assertEqual(code, 0, lines)
            rows, _ = changelog.read(t)
            self.assertEqual(rows[0]["result_commit"], "pending")
            self.assertIn("approved after being shown the literal text:", rows[0]["sign_off"])
            self.assertIn("+- new invariant", rows[0]["sign_off"])

    def test_staged_governance_without_row_is_refused_by_hook_logic(self):
        with tree() as t:
            project(t)
            write(t, "AGENTS.md", "changed" + NL)
            git(t, "add", "AGENTS.md")
            probs = governance.staged_problems(t, cfg())
            self.assertEqual(len(probs), 1)
            self.assertIn("no pending changelog row", probs[0])
            governance.record(t, cfg(), change_id="G-2", file_section="AGENTS.md", grounding="spec", shown_text="changed", approved_by="Casey")
            self.assertEqual(governance.staged_problems(t, cfg()), [])


class RangeCheck(unittest.TestCase):
    def test_governance_change_without_row_blocks_and_is_advisory(self):
        with tree() as t:
            base = project(t)
            write(t, "AGENTS.md", "rules changed" + NL)
            head = commit(t, "loosen rules")
            outs, is_gov = governance.check_range(t, cfg(), base, head, "epic-9")
            self.assertTrue(is_gov)
            g = next(o for o in outs if o.check == "governance")
            self.assertIs(g.state, State.FINDINGS)
            self.assertTrue(g.blocking)
            self.assertIn("a human decision is the accountable control", g.findings[0])

    def test_declared_surface_isolation_and_advisory_verdict(self):
        with tree() as t:
            base = project(t)
            governance.record(t, cfg(), change_id="G-3", file_section="AGENTS.md ## Project rules", grounding="decision D-9",
                              shown_text="add rule", approved_by="Casey Houle")
            write(t, "AGENTS.md", (t / "AGENTS.md").read_text(encoding="utf-8") + "- rule [decision: D-9]" + NL)
            head = commit(t, "governance: add rule")
            outs, is_gov = governance.check_range(t, cfg(), base, head, "epic-9")
            self.assertEqual([o.state for o in outs if o.check in ("governance-surface", "governance-isolation")], [State.CLEAN, State.CLEAN])
            find_advisory = next(o for o in outs if o.check == "governance-advisory")
            self.assertIn("advisory", find_advisory.detail)
            # surface violation: a second governed file not declared
            write(t, ".engine/rules/control-manifest.json", json.dumps({"scope_statement": "x", "controls": []}))
            head2 = commit(t, "governance: also manifest")
            outs, _ = governance.check_range(t, cfg(), base, head2, "epic-9")
            s = next(o for o in outs if o.check == "governance-surface")
            self.assertIs(s.state, State.FINDINGS)
            self.assertTrue(s.blocking, "a change outside the declared surface is a blocking finding, not a note")
            self.assertTrue(s.findings[0].startswith(".engine/rules/control-manifest.json: not named in the changelog row(s)"))

    def test_governance_bundled_with_feature_work_blocks(self):
        with tree() as t:
            base = project(t)
            governance.record(t, cfg(), change_id="G-4", file_section="AGENTS.md", grounding="d", shown_text="x", approved_by="Casey")
            write(t, "AGENTS.md", "rules" + NL)
            write(t, "src/feature.py", "x = 2" + NL)
            head = commit(t, "rules plus feature")
            outs, _ = governance.check_range(t, cfg(), base, head, "epic-9")
            iso = next(o for o in outs if o.check == "governance-isolation")
            self.assertIs(iso.state, State.FINDINGS)
            self.assertIn("bundled with feature work (src/feature.py)", iso.findings[0])

    def test_rules_at_base_materialised_for_review(self):
        with tree() as t:
            base = project(t)
            original = (t / "AGENTS.md").read_text(encoding="utf-8")
            write(t, "AGENTS.md", "weakened" + NL)
            head = commit(t, "weaken")
            written = governance.rules_at_base(t, base, governance.governed_set(t, cfg()), t / "out")
            self.assertIn("AGENTS.md", written)
            self.assertEqual((t / "out" / "AGENTS.md").read_text(encoding="utf-8"), original)

    def test_gate_records_advisory_for_governance_range(self):
        with tree() as t:
            base = project(t)
            governance.record(t, cfg(), change_id="G-5", file_section="AGENTS.md ## Project rules", grounding="d",
                              shown_text="x", approved_by="Casey Houle")
            write(t, "AGENTS.md", (t / "AGENTS.md").read_text(encoding="utf-8") + "- rule [decision: D-1]" + NL)
            head = commit(t, "governance")
            write(t, ".engine/work/coverage.json", json.dumps({"files": {}}))
            gatelog.write_started(t, cfg(), "epic-9", "1", f"{base[:12]}..{head[:12]}", head)
            q, s, ctx = gate.prepare(t, cfg(), "epic-9", "1", base, head)
            self.assertTrue(ctx["governance"])
            self.assertTrue((t / ".engine/work/rules-at-base-epic-9/AGENTS.md").is_file())
            checklist_text = (t / ".engine/work/gate-epic-9-1-checklist.md").read_text(encoding="utf-8")
            self.assertIn("GOVERNANCE CHANGE", checklist_text)
            from engine import checklist as cl
            v = {"verdict": "pass", "tier": "IL4", "run": "1", "range": f"{base[:12]}..{head[:12]}", "control_shaped": "no",
                 "manifest_result": "template-only", "completeness_blocks": "0", "platform_surface": "none", "scan_verdict": "n/a",
                 "open_findings": "0", "blocking_findings": "0", "tickets_opened": "0", "reviewer_class": "automated",
                 "model": "reviewer-x-70b", "attested_by": "Casey Houle", "checklist_version": cl.version(), "harness_version": "x"}
            line, probs = gate.submit(t, cfg(), "epic-9", "1", v, "Casey Houle")
            self.assertEqual(probs, [])
            rows, _ = gatelog.series(t)
            self.assertEqual(rows[-1]["verdict"], "advisory", "on a governance change the automated gate is advisory")


class Protocol(unittest.TestCase):
    def test_protocol_governs_itself(self):
        self.assertIn(governance.ZONES_FILE, governance.DEFAULT_SET)
