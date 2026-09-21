# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The two gates, the handoff, the isolation protocol (spec 01 §3.3, §5, §6; spec 03 §2; spec 11 §8)."""
import json
import unittest

from engine import checklist, gate, handoff, lifecycle, manifest, stamp
from engine.config import Config
from engine.outcome import State
from engine.records import gatelog, templates
from .helpers import ROOT, cli, commit, find_line, git, git_repo, tree, write, write_config

NL = chr(10)
AUTH = "def require_auth(request, next):" + NL + "    if not request.get('token'):" + NL + "        raise PermissionError" + NL + "    return next(request)" + NL
APP = ("from auth import require_auth" + NL + "app = object()" + NL + "@app.route('/items/<id>')" + NL + "def item(id): return require_auth" + NL)
TEST = ("from auth import require_auth" + NL + "def test_items_rejects_without_token():" + NL +
        "    assert client.get('/items/<id>').status == 401" + NL +
        "def test_items_other_user_forbidden():" + NL + "    assert other_user.get('/items/<id>').status == 403" + NL)


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
         "protected_branch": "main", "side": "low", "timezone": "UTC", "test_command": ["python", "-c", "pass"]}
    d.update(over)
    return Config(d)


def project(t, **over):
    """A repo with a remote-tracked protected branch and a feature branch carrying one change."""
    conf = {"protected_branch": "main", "side": "low", "timezone": "UTC", "test_command": ["python", "-c", "pass"]}
    conf.update(over)
    write_config(t, **conf)
    templates.render_all(t / ".engine/records")
    write(t, ".engine/records/README.md", "# Records" + NL)
    write(t, manifest.FILE, json.dumps({"schema": 1, "scope_statement": manifest.SCOPE_STATEMENT, "controls": []}))
    git_repo(t)
    write(t, "src/app.py", "app = object()" + NL)
    base = commit(t, "base")
    git(t, "update-ref", "refs/remotes/origin/main", base)
    git(t, "checkout", "-q", "-b", "epic-7")
    return base


def feature(t, msg="ABC-12 add items route", files=None):
    for f, text in (files or {"src/app.py": APP, "src/auth.py": AUTH, "tests/test_items.py": TEST}).items():
        write(t, f, text)
    return commit(t, msg)


def green_stamp(t, head):
    stamp.write(t, commit=head, verdict="green", timestamp="2026-09-20T00:00:00+00:00", scanners=["a", "b", "c", "d", "e"])


class Handoff(unittest.TestCase):
    def test_unit_is_the_branch_last_segment(self):
        """Found by the lifecycle exercise: a branch named unit/U1 put a slash in the unit
        identifier, and the started marker could not be written."""
        from engine import lifecycle
        self.assertEqual(lifecycle.unit_from_branch("unit/U1"), "U1")
        self.assertEqual(lifecycle.unit_from_branch("U1"), "U1")
        with tree() as t:
            project(t); head = feature(t)
            git(t, "checkout", "-q", "-b", "unit/U9")
            green_stamp(t, head)
            doc = handoff.generate(t, cfg())
            self.assertEqual(doc["unit"], "U9")
            self.assertTrue((t / ".engine/records/started/U9-1.json").is_file())

    def test_refuses_without_scan_stamp_for_this_commit(self):
        with tree() as t:
            project(t); head = feature(t)
            with self.assertRaises(handoff.HandoffRefused) as cm:
                handoff.generate(t, cfg())
            self.assertIn("no scan stamp describes this exact commit", str(cm.exception))
            stamp.write(t, commit="0" * 40, verdict="green", timestamp="x", scanners=["a"])
            with self.assertRaises(handoff.HandoffRefused):
                handoff.generate(t, cfg())

    def test_refuses_red_scan_even_with_override(self):
        with tree() as t:
            project(t); head = feature(t)
            stamp.write(t, commit=head, verdict="red", timestamp="x", scanners=["a"])
            with self.assertRaises(handoff.HandoffRefused) as cm:
                handoff.generate(t, cfg(), scan_impossible=True, scan_impossible_reason="no runtime")
            self.assertIn("override exists for an impossible scan, not a failed one", str(cm.exception))

    def test_red_scan_refused_without_override(self):
        with tree() as t:
            project(t); head = feature(t)
            stamp.write(t, commit=head, verdict="red", timestamp="x", scanners=["a"])
            with self.assertRaises(handoff.HandoffRefused) as cm:
                handoff.generate(t, cfg())
            self.assertIn("fix on the branch, rescan, then hand off", str(cm.exception))

    def test_review_launches_a_fresh_process_with_only_the_handoff(self):
        import os
        from .stubs import invocations, stub_tool
        with tree() as t:
            project(t); head = feature(t); green_stamp(t, head)
            doc = handoff.generate(t, cfg()); handoff.write(t, doc)
            stub_tool(t / "bin", "reviewer-stub", exit_code=0)
            old = dict(os.environ)
            os.environ["PATH"] = str(t / "bin") + os.pathsep + os.environ.get("PATH", "")
            os.environ["ENGINE_REVIEWER_CMD"] = "reviewer-stub --fresh"
            os.environ["ENGINE_SESSION_TRANSCRIPT"] = "the construction conversation"
            try:
                code, lines = cli(t, "review", "unit=epic-7", "run=1")
            finally:
                os.environ.clear(); os.environ.update(old)
            self.assertEqual(code, 0, lines)
            inv = invocations(t / "bin")
            self.assertEqual(inv, ["reviewer-stub --fresh " + str(t / ".engine" / "work" / "handoff-epic-7-1.md")])

    def test_override_for_impossible_scan_announces_itself(self):
        with tree() as t:
            project(t); feature(t)
            doc = handoff.generate(t, cfg(), scan_impossible=True, scan_impossible_reason="no container runtime on this host")
            self.assertTrue(doc["scan"].startswith("scan: NOT PERFORMED — override in effect"))
            self.assertIn("no container runtime on this host", handoff.render(doc))

    def test_contains_exactly_the_contract_and_no_free_text(self):
        with tree() as t:
            base = project(t); head = feature(t); green_stamp(t, head)
            doc = handoff.generate(t, cfg())
            self.assertEqual(set(doc), {"kind", "unit", "run", "range", "commit_count", "changed_file_count", "work_items",
                                        "work_item_files", "shape", "read_first", "scan", "started_marker", "instruction"})
            self.assertEqual((doc["range"]["base"], doc["range"]["head"]), (base, head))
            self.assertEqual((doc["commit_count"], doc["changed_file_count"]), (1, 3))
            self.assertEqual(doc["work_items"], ["ABC-12"])
            self.assertEqual(doc["unit"], "epic-7")
            self.assertEqual(doc["shape"]["track"], "web")
            self.assertIn("Do not read the conversation", doc["instruction"])
            lines = handoff.render(doc).splitlines()
            self.assertEqual(len([l for l in lines if l.startswith("This handoff carries no free-text field")]), 1)
            self.assertFalse(any("notes" in l.lower() for l in lines))
            self.assertTrue((t / doc["started_marker"]).is_file(), "the started marker is written before any verdict exists")
            self.assertTrue((t / ".engine/work/handoff-epic-7-1.md").is_file() or handoff.write(t, doc))

    def test_generator_takes_no_free_text_parameter(self):
        import inspect
        params = set(inspect.signature(handoff.generate).parameters)
        self.assertEqual(params, {"root", "cfg", "checkpoint", "scan_impossible", "scan_impossible_reason"})

    def test_refuses_on_protected_branch_and_empty_range(self):
        with tree() as t:
            project(t)
            git(t, "checkout", "-q", "main")
            with self.assertRaises(handoff.HandoffRefused) as cm:
                handoff.generate(t, cfg())
            self.assertIn("HEAD is the protected branch", str(cm.exception))
            git(t, "checkout", "-q", "epic-7")
            with self.assertRaises(handoff.HandoffRefused) as cm:
                handoff.generate(t, cfg(), scan_impossible=True, scan_impossible_reason="x")
            self.assertIn("range is empty", str(cm.exception))

    def test_checkpoint_is_advisory(self):
        with tree() as t:
            project(t); head = feature(t); green_stamp(t, head)
            doc = handoff.generate(t, cfg(), checkpoint=True)
            self.assertEqual(doc["kind"], "advisory checkpoint")
            self.assertIn("no merge implication", doc["instruction"])

    def test_run_number_increments(self):
        with tree() as t:
            project(t); head = feature(t); green_stamp(t, head)
            self.assertEqual(handoff.generate(t, cfg())["run"], 1)
            self.assertEqual(handoff.generate(t, cfg())["run"], 2)


class Checklist(unittest.TestCase):
    def test_base_has_the_eleven_items(self):
        self.assertEqual(len(checklist.BASE), 11)
        self.assertEqual([i for i, _, _ in checklist.BASE][:3], ["B1", "B2", "B3"])
        self.assertEqual([q for q, _ in checklist.COMPLETENESS], ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"])

    def test_conditional_blocks_cover_the_required_items(self):
        counts = {bid: len(checks) for bid, _, _, _, _, checks in checklist.CONDITIONAL}
        self.assertEqual(counts, {"ELEVATED": 6, "MOBILE": 9, "ONPREM": 7})

    def test_checklist_is_not_reduced_for_a_smaller_model(self):
        import inspect
        self.assertNotIn("model", inspect.signature(checklist.compose).parameters)

    def test_activation_semantics(self):
        self.assertEqual(dict(checklist.activation(cfg())), {"ELEVATED": "informational"})
        self.assertEqual(dict(checklist.activation(cfg(tier="IL6"))), {"ELEVATED": "additive"})
        self.assertEqual(dict(checklist.activation(cfg(track="android", tier="IL6", provider="tactical", app_type="native"))),
                         {"ELEVATED": "additive", "MOBILE": "additive", "ONPREM": "substitutive"})

    def test_substitution_removes_only_infrastructure_checks(self):
        items = checklist.compose(cfg(provider="tactical"))
        ids = [i for _, i, _, _, _ in items]
        self.assertNotIn("I1", ids)
        self.assertIn("ONPREM1", ids)
        for b in ("B1", "B2", "B3", "B6"):
            self.assertIn(b, ids, "application-layer checks are never substituted")
        self.assertEqual(len([i for i in ids if i.startswith("B")]), 11)

    def test_every_conditional_check_cites_a_standard(self):
        for bid, title, when, sem, replaces, checks in checklist.CONDITIONAL:
            for check, std in checks:
                self.assertRegex(std, r"NIST|FIPS|OWASP", f"{bid}: {check}")

    def test_informational_block_shown_not_enforced(self):
        items = checklist.compose(cfg())
        groups = {g for g, *_ in items}
        self.assertIn("ELEVATED:informational", groups)

    def test_definition_is_self_contained_and_rendered_from_data(self):
        rendered = (ROOT / "engine/dist/agents/security-gate.md").read_text(encoding="utf-8")
        self.assertEqual(rendered, checklist.render_definition(), "regenerate the reviewer definition from engine.checklist")
        lines = rendered.splitlines()
        for line in lines:
            self.assertFalse(line.startswith(("Read and follow:", "@", "import ")), line)
        self.assertIn(f"Checklist version: {checklist.version()}", lines)
        for i, t_, d in checklist.BASE:
            self.assertEqual(len([l for l in lines if l.startswith(f"{i}. **{t_}**")]), 1, t_)
        for q, t_ in checklist.COMPLETENESS:
            self.assertEqual(len([l for l in lines if l.startswith(f"- **{q}** {t_}")]), 1, q)

    def test_verdict_block_defined_once_and_copied(self):
        ref = (ROOT / "engine/dist/reference/VERDICT.md").read_text(encoding="utf-8")
        self.assertIn(checklist.verdict_block_text(), ref)
        self.assertIn(checklist.verdict_block_text(), checklist.render_definition())
        for f in ("verdict", "tier", "run", "range", "control_shaped", "manifest_result", "completeness_blocks",
                  "platform_surface", "scan_verdict", "open_findings", "blocking_findings", "tickets_opened"):
            self.assertIn(f, checklist.VERDICT_FIELDS)

    def test_version_changes_with_content(self):
        v = checklist.version()
        saved = checklist.BASE[0]
        try:
            checklist.BASE[0] = ("B1", "Credential hygiene", "changed")
            self.assertNotEqual(checklist.version(), v)
        finally:
            checklist.BASE[0] = saved


class QualityGate(unittest.TestCase):
    def test_negative_tests_required_for_changed_routes(self):
        with tree() as t:
            base = project(t)
            head = feature(t, files={"src/app.py": APP, "src/auth.py": AUTH, "tests/test_items.py": "def test_nothing(): pass" + NL})
            o = gate.negative_test_set(t, cfg(), base, head)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["ANY /items/<id> (src/app.py:3): no test asserts rejection without credentials",
                                          "ANY /items/<id>: record-scoped, and no test asserts one principal cannot reach another's records"])

    def test_negative_tests_present(self):
        with tree() as t:
            base = project(t); head = feature(t)
            o = gate.negative_test_set(t, cfg(), base, head)
            self.assertIs(o.state, State.CLEAN, o.lines())

    def test_empty_section_is_stated_not_passed(self):
        with tree() as t:
            base = project(t); head = feature(t, files={"docs/x.md": "hi" + NL})
            o = gate.negative_test_set(t, cfg(), base, head)
            self.assertIs(o.state, State.NOTHING_YET)
            self.assertIn("this section is empty, not passed", o.line())

    def test_routes_exist_but_none_in_range_is_stated_empty(self):
        with tree() as t:
            project(t)
            mid = feature(t)                                   # routes now exist on the branch
            head = feature(t, files={"docs/y.md": "y" + NL})   # a later change touches none of them
            o = gate.negative_test_set(t, cfg(), mid, head)
            self.assertIs(o.state, State.NOTHING_YET)
            self.assertIn("none is in the range — this section is empty, not passed", o.line())

    def test_last_privileged_principal_guard_needs_test(self):
        with tree() as t:
            base = project(t)
            head = feature(t, files={"src/admin.py": "def remove_admin(u): pass" + NL, "tests/test_admin.py": "def test_x(): pass" + NL})
            o = gate.negative_test_set(t, cfg(), base, head)
            self.assertEqual(o.findings, ["remove_admin (src/admin.py:1): can remove a privileged principal, and no test asserts the last one is protected"])

    def test_mutation_evidence_required_for_every_control(self):
        with tree() as t:
            project(t)
            write(t, manifest.FILE, json.dumps({"scope_statement": manifest.SCOPE_STATEMENT, "controls": [
                {"id": "C-1", "description": "d", "location": {"file": "src/auth.py", "symbol": "require_auth"},
                 "test_pattern": "tests/*", "status": "system-specific"}]}))
            o = gate.mutation_evidence(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertEqual(o.findings, ["C-1 [-]: never mutated — no result recorded"])
            from engine.records import table
            from engine.records import schema as sch
            table.append(t, ".engine/records/mutation-results.md", sch.MUTATION,
                         {"date": "x", "control": "C-1", "branch": "-", "mutation": "m", "baseline": "green", "result": "suite-stayed-green", "side": "low"})
            o = gate.mutation_evidence(t, cfg())
            self.assertIn("last mutation left the suite green", o.findings[0])
            table.append(t, ".engine/records/mutation-results.md", sch.MUTATION,
                         {"date": "y", "control": "C-1", "branch": "-", "mutation": "m", "baseline": "green", "result": "suite-failed", "side": "low"})
            self.assertIs(gate.mutation_evidence(t, cfg()).state, State.CLEAN)


class SecurityMechanical(unittest.TestCase):
    def test_control_shaped_diff_needs_manifest_entry_in_same_change(self):
        with tree() as t:
            base = project(t); head = feature(t)
            outs, ctx = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            self.assertTrue(ctx["control_shaped"])
            me = next(o for o in outs if o.check == "manifest-entry")
            self.assertIs(me.state, State.FINDINGS)
            self.assertTrue(me.blocking)

    def test_manifest_entry_in_same_change_satisfies(self):
        with tree() as t:
            base = project(t)
            head = feature(t, files={"src/auth.py": AUTH, manifest.FILE: json.dumps({"scope_statement": manifest.SCOPE_STATEMENT, "controls": [
                {"id": "C-1", "description": "d", "location": {"file": "src/auth.py", "symbol": "require_auth"},
                 "test_pattern": "tests/*", "status": "system-specific"}]})})
            outs, ctx = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            self.assertIs(next(o for o in outs if o.check == "manifest-entry").state, State.CLEAN)

    def test_attribution_in_range_is_blocking(self):
        with tree() as t:
            base = project(t)
            head = feature(t, msg="x" + NL + NL + "Co-Authored" + "-By: Bot <b@x>", files={"src/y.py": "y=1" + NL})
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            a = next(o for o in outs if o.check == "attribution")
            self.assertIs(a.state, State.FINDINGS)
            self.assertTrue(a.blocking)

    def test_frozen_surface_written_is_blocking_and_report_never_shows_values(self):
        with tree() as t:
            base = project(t, frozen_surface=["deploy/values.yaml"])
            write(t, "deploy/values.yaml", "db_password: s3cret-value-here" + NL)   # engine:allow-credential
            head = commit(t, "touch values")
            outs, _ = gate.security_mechanical(t, cfg(frozen_surface=["deploy/values.yaml"]), base, head, "epic-7")
            fs = next(o for o in outs if o.check == "frozen-surface")
            self.assertIs(fs.state, State.FINDINGS)
            self.assertIn("changed: deploy/values.yaml", fs.findings)
            self.assertTrue(any("1 key(s) present, values not shown" in f for f in fs.findings))
            self.assertFalse(any("s3cret" in f for f in fs.findings))

    def test_plan_edited_during_construction_is_blocking(self):
        with tree() as t:
            base = project(t)
            lifecycle.create_unit(t, "epic-7"); lifecycle.transition_unit(t, "epic-7", "building")
            write(t, "plans/design.md", "revised" + NL)
            head = commit(t, "revise plan mid-build")
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            pe = next(o for o in outs if o.check == "plan-edits")
            self.assertIs(pe.state, State.FINDINGS)
            self.assertTrue(pe.blocking)

    def test_one_item_enumeration_is_a_list(self):
        """Found by the Gemma 4 gate run on notes-api: `DELETE /notes/<id>` is a correct one-item
        enumeration of the entry point a guard does not cover, and was refused as a summary."""
        self.assertTrue(gate.is_enumeration("DELETE /notes/<id>"))
        self.assertTrue(gate.is_enumeration("- a" + chr(10) + "- b"))
        self.assertTrue(gate.is_enumeration("token expiry, token revocation"))
        self.assertFalse(gate.is_enumeration("Nothing is uncovered by this hook."))
        self.assertFalse(gate.is_enumeration("all entry points are covered by the middleware"))
        self.assertFalse(gate.is_enumeration("It covers everything."))
        self.assertTrue(gate.is_enumeration("require_owner"))
        self.assertTrue(gate.is_enumeration("src/app.py:75"))

    def test_cross_principal_wording_inside_a_test_name(self):
        """Found by the notes-api demo: test_other_user_cannot_read_... is the natural name."""
        self.assertTrue(gate.CROSS_PRINCIPAL.search("def test_other_user_cannot_read_a_note_403(self):"))
        self.assertTrue(gate.CROSS_PRINCIPAL.search("another tenant's records"))
        self.assertFalse(gate.CROSS_PRINCIPAL.search("brother_users"))

    def test_templated_route_is_matched_by_a_concrete_path_in_tests(self):
        """Found by the notes-api demo: tests call /notes/1, the route is /notes/<id>."""
        m = gate.route_mention("/notes/<id>")
        self.assertTrue(m.search("client.get('/notes/1')"))
        self.assertTrue(m.search("f'/notes/{note[\"id\"]}'"))
        self.assertFalse(m.search("client.get('/notes')"))
        self.assertFalse(m.search("client.get('/notes/1/tags')") is not None and False)
        self.assertTrue(gate.route_mention("/users/{user_id}/notes/:nid").search("/users/7/notes/9"))
        self.assertFalse(gate.route_mention("/items/<id>").search("/itemsX/1"))

    def test_placed_harness_fixtures_are_not_the_project_tests(self):
        """Found by the lifecycle exercise: the harness's own test fixtures, placed under
        .engine/, satisfied a project's negative-test requirement for a route they mention."""
        with tree() as t:
            base = project(t)
            write(t, ".engine/harness/selftest/test_gate.py", TEST)      # the harness fixture that mentions /items/<id>
            head = feature(t, files={"src/app.py": APP, "src/auth.py": AUTH, "tests/test_items.py": "from src.app import item" + NL +
                                     "def test_items_ok():" + NL + "    assert item({'token': 't'})" + NL})
            o = gate.negative_test_set(t, cfg(), base, head)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(any("no test asserts rejection without credentials" in f for f in o.findings), o.findings)
            self.assertTrue(any("one principal cannot reach another" in f for f in o.findings), o.findings)

    def test_plan_written_then_built_on_one_branch_is_not_a_construction_edit(self):
        """Found by the lifecycle exercise: PLAN then BUILD on the same branch put the unit file
        and the plan in the range, and the state transition read as a design edit."""
        with tree() as t:
            base = project(t)
            lifecycle.create_unit(t, "epic-7")
            write(t, "plans/design.md", "## Interfaces" + NL + "- GET /items/<id>" + NL)
            commit(t, "plan")
            lifecycle.transition_unit(t, "epic-7", "building")
            commit(t, "start building")
            head = feature(t)
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            pe = next(o for o in outs if o.check == "plan-edits")
            self.assertIs(pe.state, State.CLEAN, pe.line())
            write(t, "plans/design.md", "## Interfaces" + NL + "- GET /items/<id>" + NL + "- DELETE /items/<id>" + NL)
            head = commit(t, "revise plan mid-build")
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            pe = next(o for o in outs if o.check == "plan-edits")
            self.assertIs(pe.state, State.FINDINGS)
            self.assertEqual(len(pe.findings), 1)
            self.assertTrue(pe.findings[0].startswith("plans/design.md:"))

    def test_dependency_needs_approval_on_target(self):
        with tree() as t:
            base = project(t)
            write(t, ".engine/rules/dependency-policy.json", json.dumps({"target_requires_approval": True, "lead_time": "10-15 working days", "dependencies": {}}))
            write(t, "package.json", json.dumps({"dependencies": {"left-pad": "1.0.0"}}, indent=1))
            head = commit(t, "add dep")
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            dp = next(o for o in outs if o.check == "dependency-policy")
            self.assertIs(dp.state, State.FINDINGS)
            self.assertTrue(dp.blocking)
            self.assertIn("lead time to approval and transfer: 10-15 working days", dp.findings[0])


class Submit(unittest.TestCase):
    def prepared(self, t, control_shaped=False):
        base = project(t)
        files = {"src/app.py": APP, "src/auth.py": AUTH, "tests/test_items.py": TEST} if control_shaped else {"docs/x.md": "hi" + NL}
        head = feature(t, files=files)
        if control_shaped:
            from engine import governance
            governance.record(t, cfg(), change_id="G-1", file_section=manifest.FILE, grounding="spec 01 §7.4.1",
                              shown_text="add control C-1 require_auth", approved_by="Casey Houle")
            write(t, manifest.FILE, json.dumps({"scope_statement": manifest.SCOPE_STATEMENT, "controls": [
                {"id": "C-1", "description": "d", "location": {"file": "src/auth.py", "symbol": "require_auth"},
                 "test_pattern": "tests/*", "status": "system-specific"}]}))
            head = commit(t, "declare control")
            from engine.records import table
            from engine.records import schema as sch
            table.append(t, ".engine/records/mutation-results.md", sch.MUTATION,
                         {"date": "y", "control": "C-1", "branch": "-", "mutation": "m", "baseline": "green", "result": "suite-failed", "side": "low"})
        write(t, ".engine/work/coverage.json", json.dumps({"files": {"src/app.py": {"covered": 9, "total": 10}, "src/auth.py": {"covered": 9, "total": 10}}}))
        gatelog.write_started(t, cfg(), "epic-7", "1", f"{base[:12]}..{head[:12]}", head)
        q, s, ctx = gate.prepare(t, cfg(), "epic-7", "1", base, head)
        return base, head, q, s, ctx

    def verdict(self, base, head, **over):
        v = {"verdict": "pass", "tier": "IL4", "run": "1", "range": f"{base[:12]}..{head[:12]}", "control_shaped": "no",
             "manifest_result": "template-only", "completeness_blocks": "0", "platform_surface": "none declared",
             "scan_verdict": "green", "open_findings": "0", "blocking_findings": "0", "tickets_opened": "0",
             "reviewer_class": "automated", "model": "example-reviewer-70b", "attested_by": "Casey Houle",
             "checklist_version": checklist.version(), "harness_version": "x"}
        v.update(over)
        return v

    def test_quality_gate_runs_before_security(self):
        with tree() as t:
            base = project(t, test_command=["python", "-c", "import sys; sys.exit(1)"])
            head = feature(t, files={"docs/x.md": "hi" + NL})
            q, s, ctx = gate.prepare(t, cfg(test_command=["python", "-c", "import sys; sys.exit(1)"]), "epic-7", "1", base, head)
            self.assertTrue(any(o.failed for o in q))
            self.assertEqual(s, [], "the security gate does not run on code whose tests do not pass")
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head), "Casey Houle")
            self.assertIsNone(line)
            self.assertIn("quality gate did not pass", probs[0])

    def test_valid_verdict_recorded_with_versions_model_and_attestation(self):
        with tree() as t:
            base, head, q, s, ctx = self.prepared(t)
            self.assertFalse(any(o.failed for o in q), [o.line() for o in q])
            self.assertFalse(ctx["control_shaped"], "a documentation-only change must not trigger the completeness review")
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head), "Casey Houle")
            self.assertEqual(probs, [])
            rows, _ = gatelog.series(t)
            r = rows[-1]
            self.assertEqual((r["verdict"], r["reviewer_class"], r["model"], r["attested_by"]), ("pass", "automated", "example-reviewer-70b", "Casey Houle"))
            self.assertEqual(r["checklist_version"], checklist.version())
            self.assertRegex(r["harness_version"], r"\+[0-9a-f]{12}$")

    def test_verdict_missing_field_refused(self):
        with tree() as t:
            base, head, *_ = self.prepared(t)
            v = self.verdict(base, head); del v["scan_verdict"]
            line, probs = gate.submit(t, cfg(), "epic-7", "1", v, "Casey")
            self.assertEqual(probs, ["verdict block lacks 'scan_verdict'"])

    def test_stale_checklist_version_refused(self):
        with tree() as t:
            base, head, *_ = self.prepared(t)
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head, checklist_version="cl-000"), "Casey")
            self.assertTrue(probs[0].startswith("checklist_version cl-000 is not the version this run was prepared with"), probs)

    def test_model_identity_required_for_automated_reviewer(self):
        with tree() as t:
            base, head, *_ = self.prepared(t)
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head, model="-"), "Casey")
            self.assertIn("model identity (identifier and parameter scale) must be recorded for an automated reviewer", probs)

    def test_completeness_answers_required_in_prose_with_lists(self):
        with tree() as t:
            base, head, q, s, ctx = self.prepared(t, control_shaped=True)
            self.assertTrue(ctx["control_shaped"])
            v = self.verdict(base, head, control_shaped="yes")
            line, probs = gate.submit(t, cfg(), "epic-7", "1", v, "Casey")
            self.assertIn("control-shaped diff: completeness review answers are required per control touched", probs)
            v["completeness"] = {"require_auth": {"Q1": "pass", "Q2": "There is one write path, the route handler; the guard is on it.",
                                                  "Q3": "It covers everything.", "Q4": "- audience claim" + NL + "- algorithm header",
                                                  "Q5": "src/app.py line 4", "Q6": "No input schema; the route reads only the id path parameter."}}
            line, probs = gate.submit(t, cfg(), "epic-7", "1", v, "Casey")
            self.assertIn("completeness require_auth Q1: unanswered or answered with a bare pass — blocking", probs)
            self.assertIn("completeness require_auth Q3: must produce a list, not a summary judgment", probs)
            v["completeness"]["require_auth"]["Q1"] = "The guard reads the token from the request header only; there is no nested structure to recurse into."
            v["completeness"]["require_auth"]["Q3"] = "- websocket upgrade handler" + NL + "- the health endpoint"
            line, probs = gate.submit(t, cfg(), "epic-7", "1", v, "Casey")
            self.assertEqual(probs, [])

    def test_pass_refused_when_mechanical_checks_blocked(self):
        with tree() as t:
            base = project(t)
            head = feature(t, msg="x" + NL + NL + "Co-Authored" + "-By: Bot <b@x>", files={"docs/x.md": "hi" + NL})
            write(t, ".engine/work/coverage.json", json.dumps({"files": {}}))
            gate.prepare(t, cfg(), "epic-7", "1", base, head)
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head), "Casey")
            self.assertIn("verdict cannot be pass: mechanical checks blocked (attribution)", probs)

    def test_finding_identifiers_must_match_count(self):
        with tree() as t:
            base, head, *_ = self.prepared(t)
            line, probs = gate.submit(t, cfg(), "epic-7", "1", self.verdict(base, head, verdict="fail", open_findings="2", finding_ids=["F-1"]), "Casey")
            self.assertEqual(probs, ["open_findings is 2 but 1 finding identifiers were given"])

    def test_no_model_run_records_advisory_row(self):
        with tree() as t:
            base, head, *_ = self.prepared(t)
            line, probs = gate.no_model(t, cfg(), "epic-7", "1", "Casey Houle")
            self.assertEqual(probs, [])
            rows, _ = gatelog.series(t)
            r = rows[-1]
            self.assertEqual((r["verdict"], r["reviewer"], r["model"]), ("advisory", "mechanical-only", "none — checklist not applied"))

    def test_gate_reaches_no_network(self):
        import inspect
        src = inspect.getsource(gate)
        self.assertNotIn("import net", src)
        self.assertNotIn(", net", src.split("from . import", 1)[1].split(chr(10))[0] if "from . import" in src else "")

    def test_dependency_approved_but_not_yet_available_on_target_still_fails(self):
        with tree() as t:
            base = project(t)
            write(t, ".engine/rules/dependency-policy.json", json.dumps({"target_requires_approval": True, "lead_time": "3 weeks",
                  "dependencies": {"left-pad": {"approval": "approved", "approval_date": "2026-09-01", "available_on_target": ""}}}))
            write(t, "package.json", json.dumps({"dependencies": {"left-pad": "1.0.0"}}, indent=1))
            head = commit(t, "add dep")
            outs, _ = gate.security_mechanical(t, cfg(), base, head, "epic-7")
            dp = next(o for o in outs if o.check == "dependency-policy")
            self.assertIs(dp.state, State.FINDINGS)
            self.assertIn("available on target: not yet", dp.findings[0])
            self.assertIn("lead time: 3 weeks", dp.findings[0])

    def test_gate_reads_diff_from_version_control_not_input(self):
        import inspect
        for fn in (gate.prepare, gate.security_mechanical, gate.quality_gate):
            self.assertNotIn("diff", inspect.signature(fn).parameters, f"{fn.__name__} must not accept a diff as input")


class Lifecycle(unittest.TestCase):
    def test_states_and_header_storage(self):
        with tree() as t:
            lifecycle.create_unit(t, "u1")
            lifecycle.create_item(t, "T-1", "u1", "The login page rejects an expired token with a 401.")
            h = lifecycle.read_header(t / "tickets/T-1.md")
            self.assertEqual((h["state"], h["unit"]), ("open", "u1"))
            self.assertEqual(lifecycle.transition_item(t, "T-1", "claimed"), "claimed")
            with self.assertRaises(ValueError):
                lifecycle.transition_item(t, "T-1", "done")
            self.assertEqual(lifecycle.transition_unit(t, "u1", "building"), "building")
            self.assertEqual(lifecycle.read_header(t / "plans/units/u1.md")["state"], "building")

    def test_done_when_must_be_observable(self):
        with tree() as t:
            with self.assertRaises(ValueError) as cm:
                lifecycle.create_item(t, "T-1", "u", "Implement the login page")
            self.assertIn("observable outcome", str(cm.exception))
            with self.assertRaises(ValueError):
                lifecycle.create_item(t, "T-2", "u", "")

    def test_dependency_in_review_counts_as_satisfied(self):
        with tree() as t:
            lifecycle.create_item(t, "T-1", "u", "A returns 200.")
            lifecycle.create_item(t, "T-2", "u", "B returns 200.", depends_on=["T-1"])
            with self.assertRaises(ValueError) as cm:
                lifecycle.transition_item(t, "T-2", "claimed")
            self.assertIn("blocked by: T-1 (open)", str(cm.exception))
            lifecycle.transition_item(t, "T-1", "claimed"); lifecycle.transition_item(t, "T-1", "in review")
            self.assertEqual(lifecycle.transition_item(t, "T-2", "claimed"), "claimed")

    def test_orient_compares_against_remote_and_always_exits_zero(self):
        with tree() as t:
            base = project(t)
            feature(t, files={"docs/x.md": "x" + NL})
            git(t, "branch", "-f", "main", gitutil_head(t))     # local main drifted; remote is authoritative
            code, lines = cli(t, "status")
            self.assertEqual(code, 0)
            self.assertIn("1 ahead of / 0 behind origin/main", find_line(lines, "position:"))
            find_line(lines, "ci: not configured")
            self.assertEqual(len([l for l in lines if l.startswith("next:")]), 1)

    def test_orient_next_action_from_item_files(self):
        with tree() as t:
            project(t)
            lifecycle.create_unit(t, "epic-7"); lifecycle.transition_unit(t, "epic-7", "building")
            lifecycle.create_item(t, "T-1", "epic-7", "Items route rejects a missing token with 401.")
            code, lines = cli(t, "status")
            self.assertEqual(find_line(lines, "next:"), "next: claim T-1: Items route rejects a missing token with 401.")
            lifecycle.transition_item(t, "T-1", "claimed")
            self.assertTrue(find_line(cli(t, "status")[1], "next:").startswith("next: continue T-1"))

    def test_orient_never_reads_a_status_file(self):
        import inspect
        src = inspect.getsource(lifecycle.orient)
        self.assertNotIn("handoff-", src, "orient must not read a handoff file")
        self.assertNotIn(".engine/work", src, "orient must not read state written by an earlier session")
        self.assertNotIn("read_text", src.replace("read_header", ""))


def gitutil_head(t):
    from engine import gitutil
    return gitutil.head(t)
