# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The command-line layer of every subcommand: usage lines, COULD NOT RUN / REFUSED paths, exit codes and printed output."""
import json
import os
import pathlib
import types
import unittest
from unittest import mock

from engine import __main__ as cli_main
from engine import catalogue, field, gate, governance, handoff, manifest, mutate
from engine.scan import alarm, bundles, runner
from .helpers import cli, commit, find_line, git_repo, tree, write, write_config

NL = chr(10)


class Out:
    """A stand-in outcome: the CLI only reads lines(), exit_code and failed."""
    def __init__(self, lines=("[x] CLEAN",), exit_code=0, failed=False):
        self._lines, self.exit_code, self.failed = list(lines), exit_code, failed

    def lines(self):
        return list(self._lines)


class Finding:
    def __init__(self, text):
        self.text = text

    def line(self):
        return self.text


def scan_result(**over):
    r = {"ran": ["sast", "sca"], "data_age": 3, "problems": ["one problem"], "actionable": [Finding("F-1 high")],
         "carried": [Finding("F-2 low")], "closed": ["F-3"], "aged": ["F-4 past review-by"], "findings": [],
         "informational": [], "alarm": "raised", "verdict": "red", "head": "a" * 40}
    r.update(over)
    return r


def fake_scan(result=None, error=None):
    sc = mock.MagicMock()
    sc.engine = "docker"
    if error:
        sc.run.side_effect = error
    else:
        sc.run.return_value = result or scan_result()
    return mock.patch.object(runner, "Scan", return_value=sc), sc


class NoConfig(unittest.TestCase):
    """Every command that needs the project configuration says so instead of a traceback."""

    def test_unconfigured_tree_could_not_run(self):
        cases = [("scan",), ("gate", "prepare"), ("mutate",), ("handoff",), ("probe",), ("currency",),
                 ("governance", "show"), ("field", "status"), ("export", "package"), ("topology", "status"),
                 ("record", "gate-log")]
        with tree() as t:
            for args in cases:
                with self.subTest(args=args):
                    code, out = cli(t, *args)
                    self.assertEqual(code, 2, out)
                    self.assertTrue(any("COULD NOT RUN" in l for l in out), out)

    def test_config_reports_the_missing_configuration(self):
        with tree() as t:
            code, out = cli(t, "config")
            self.assertEqual(code, 1)
            self.assertTrue(out[0].startswith("config: "), out)
            code, out = cli(t, "degradation")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("degradation: COULD NOT RUN"), out)

    def test_unknown_command_prints_the_usage(self):
        with tree() as t:
            code, out = cli(t, "no-such-command")
            self.assertEqual(code, 2)
            self.assertIn("The command line. `python -m engine <command>`.", out)


class Config(unittest.TestCase):
    def test_config_prints_data_and_unset_axes(self):
        with tree() as t:
            write_config(t, tier="unset")
            code, out = cli(t, "config")
            self.assertEqual(code, 0)
            data = json.loads(NL.join(l for l in out if not l.startswith(("problem:", "not yet chosen:"))))
            self.assertEqual(data["track"], "web")
            self.assertTrue(any(l.startswith("not yet chosen: ") or l.startswith("problem: ") for l in out), out)

    def test_degradation_prints_the_statement(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "degradation")
            self.assertEqual(code, 0)
            self.assertEqual(out[0], "# Degradation statement")


class ProjectPlacement(unittest.TestCase):
    def test_update_and_adopt_refuse_a_missing_directory(self):
        with tree() as t:
            for cmd in ("update", "adopt"):
                code, out = cli(t, cmd, "--project", str(t / "absent"))
                self.assertEqual(code, 2)
                self.assertTrue(out[0].startswith(f"{cmd}: COULD NOT RUN"), out)

    def test_adopt_reports_the_inventoried_count(self):
        with tree() as t:
            with mock.patch.object(cli_main.distribute, "adopt", return_value=(Out(["placed: x"]), 4)) as m:
                code, out = cli(t, "adopt", "--project", str(t))
            self.assertEqual(code, 0)
            self.assertEqual(m.call_args[0][0], t.resolve())
            self.assertEqual(out[0], "placed: x")
            self.assertTrue(out[1].startswith("adopt: 4 pre-existing file(s) inventoried as never assessed"), out)


class Coverage(unittest.TestCase):
    REP = {"files": {"a.py": {"covered": 3, "total": 4}, "b.py": {"covered": 1, "total": 4}}}

    def test_harness_coverage_runs_the_selftests(self):
        def collect(root, suite, prefix=None):
            suite()
            return self.REP
        with tree() as t:
            with mock.patch.object(cli_main.coverage, "collect", side_effect=collect), \
                    mock.patch.object(cli_main, "run_selftests", return_value={}) as rs:
                code, out = cli(t, "coverage")
            self.assertEqual(code, 0)
            rs.assert_called_once()
            self.assertEqual(out, ["coverage: 4/8 executable lines (50.0%) across 2 harness modules -> .engine/work/coverage.json"])

    def test_project_coverage_runs_the_project_tests(self):
        def collect(root, suite, prefix=None):
            suite()
            self.assertEqual(prefix, "lib")
            return {"files": {}}
        with tree() as t:
            write(t, "cli_cov_tests/__init__.py", "")
            saved = list(__import__("sys").path)
            try:
                with mock.patch.object(cli_main.coverage, "collect", side_effect=collect):
                    code, out = cli(t, "coverage", "project", "source=lib", "tests=cli_cov_tests")
            finally:
                __import__("sys").path[:] = saved
            self.assertEqual(code, 2, "no executable lines measured is not a result")
            self.assertEqual(out, ["coverage: 0/0 executable lines (0.0%) across 0 lib/ modules -> .engine/work/coverage.json"])


class CredentialAndDirective(unittest.TestCase):
    def test_credential_scan_of_the_tree(self):
        from engine.checks import credential_scan
        with tree() as t:
            with mock.patch.object(credential_scan, "run", return_value=Out(["[credential-scan] FAILED"], exit_code=1)):
                code, out = cli(t, "credential-scan")
            self.assertEqual((code, out), (1, ["[credential-scan] FAILED"]))

    def test_accept_directive_needs_three_arguments(self):
        with tree() as t:
            code, out = cli(t, "accept-directive", "only-key")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("accept-directive KEY"), out)


class Record(unittest.TestCase):
    def test_usage_and_unknown_kind(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "record")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("record <gate-log|"), out)
            code, out = cli(t, "record", "nonsense")
            self.assertEqual((code, out), (2, ["record: unknown kind 'nonsense'"]))

    def test_missing_key_is_refused(self):
        with tree() as t:
            write_config(t)
            for kind in ("finding", "changelog", "started", "supersede", "rotate"):
                with self.subTest(kind=kind):
                    code, out = cli(t, "record", kind)
                    self.assertEqual(code, 1)
                    self.assertTrue(out[0].startswith("record: REFUSED — missing '"), out)

    def test_each_kind_reaches_its_record(self):
        from engine.records import changelog, findings, gatelog
        with tree() as t:
            write_config(t)
            with mock.patch.object(findings, "add_check", return_value="FC row") as ac, \
                    mock.patch.object(findings, "add_risk", return_value="R row") as ar, \
                    mock.patch.object(changelog, "add", return_value="CL row") as cl, \
                    mock.patch.object(gatelog, "write_started", return_value=pathlib.Path("m.json")), \
                    mock.patch.object(gatelog, "supersede", return_value="SS row"), \
                    mock.patch.object(gatelog, "rotate", return_value=3):
                self.assertEqual(cli(t, "record", "finding", "id=F-1", "class=c", "mechanism=m", "lives_in=l", "decided_by=d"),
                                 (0, ["record: finding: FC row"]))
                self.assertEqual(ac.call_args.kwargs["status"], "active")
                self.assertEqual(cli(t, "record", "risk", "id=R-1", "owner=o"), (0, ["record: risk: R row"]))
                self.assertEqual(ar.call_args.kwargs, {"id": "R-1", "owner": "o"})
                self.assertEqual(cli(t, "record", "changelog", "change_id=C1", "file_section=f", "base_commit=b",
                                     "grounding=g", "sign_off=s", "retroactive=yes"), (0, ["record: changelog: CL row"]))
                self.assertTrue(cl.call_args.kwargs["retroactive"])
                self.assertEqual(cl.call_args.kwargs["result_commit"], "pending")
                self.assertEqual(cli(t, "record", "started", "unit=U1", "run=1", "range=a..b", "head=b"),
                                 (0, ["record: started: m.json"]))
                self.assertEqual(cli(t, "record", "supersede", "unit=U1", "run=1", "wrong=w", "found=f", "disposition=d",
                                     "attested_by=a", "reviewer=r"), (0, ["record: supersede: SS row"]))
                self.assertEqual(cli(t, "record", "rotate", "period=2026"),
                                 (0, ["record: rotate: 3 row(s) rotated into gate-log.2026.md"]))


class Manifest(unittest.TestCase):
    def test_unreadable_manifest_could_not_run(self):
        with tree() as t:
            with mock.patch.object(manifest, "verify", side_effect=manifest.ManifestError("bad json")):
                code, out = cli(t, "manifest")
            self.assertEqual((code, out), (2, ["manifest: COULD NOT RUN — bad json"]))

    def test_structural_problems_are_listed(self):
        with tree() as t:
            with mock.patch.object(manifest, "verify", return_value=("unresolved", [], ["control C-1 lacks a test"])):
                code, out = cli(t, "manifest")
            self.assertEqual((code, out), (1, ["manifest: unresolved", "  - control C-1 lacks a test"]))


class Mutate(unittest.TestCase):
    def test_could_not_run_without_a_manifest(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(manifest, "load", side_effect=manifest.ManifestError("no manifest")):
                code, out = cli(t, "mutate")
            self.assertEqual((code, out), (2, ["mutate: COULD NOT RUN — no manifest"]))

    def test_no_controls_is_nothing_to_check(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(manifest, "load", return_value={}), mock.patch.object(manifest, "real_controls", return_value=[]):
                code, out = cli(t, "mutate")
            self.assertEqual(code, 0)
            self.assertTrue(out[0].startswith("mutate: NOTHING TO CHECK YET"), out)

    def test_mutation_results_and_verdict(self):
        res = {"results": [{"control": "C-1", "branch": "deny", "verdict": "suite-failed", "mutation": "return True"},
                           {"control": "C-2", "branch": "allow", "verdict": "suite-passed", "mutation": "skip check"}]}
        with tree() as t:
            write_config(t)
            with mock.patch.object(manifest, "load", return_value={}), mock.patch.object(manifest, "real_controls", return_value=["C"]):
                with mock.patch.object(mutate, "run", return_value={"reason": "suite does not run"}):
                    self.assertEqual(cli(t, "mutate"), (2, ["mutate: COULD NOT RUN — suite does not run"]))
                with mock.patch.object(mutate, "run", return_value=res):
                    code, out = cli(t, "mutate")
                self.assertEqual(code, 1)
                self.assertEqual(out[:2], ["  C-1 [deny]: suite-failed — return True", "  C-2 [allow]: suite-passed — skip check"])
                self.assertTrue(out[2].startswith("mutate: FAIL — 1 mutation(s) failed the suite, 1 did not"), out)
                with mock.patch.object(mutate, "run", return_value={"results": res["results"][:1]}):
                    code, out = cli(t, "mutate")
                self.assertEqual(code, 0)
                self.assertTrue(out[-1].startswith("mutate: PASS — 1 mutation(s) failed the suite, 0 did not"), out)


class Handoff(unittest.TestCase):
    def test_refused_and_written(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(handoff, "generate", side_effect=handoff.HandoffRefused("no scan stamp")):
                self.assertEqual(cli(t, "handoff"), (1, ["handoff: REFUSED — no scan stamp"]))
            doc = {"unit": "U1"}
            with mock.patch.object(handoff, "generate", return_value=doc) as g, \
                    mock.patch.object(handoff, "write", return_value=t / ".engine/work/handoff-U1-1.md"), \
                    mock.patch.object(handoff, "render", return_value="# Handoff U1"):
                code, out = cli(t, "handoff", "--checkpoint", "--scan-impossible", "scanner image absent")
            self.assertEqual((code, out), (0, ["# Handoff U1", "handoff: written to .engine/work/handoff-U1-1.md"]))
            self.assertEqual(g.call_args.kwargs, {"checkpoint": True, "scan_impossible": True,
                                                  "scan_impossible_reason": "scanner image absent"})


class Gate(unittest.TestCase):
    def test_usage_and_unknown(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "gate")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("gate prepare unit=<u>"), out)
            self.assertEqual(cli(t, "gate", "bogus"), (2, ["gate: unknown subcommand 'bogus'"]))

    def test_prepare_with_unparseable_handoff_and_unresolvable_base(self):
        with tree() as t:
            write_config(t)
            git_repo(t)
            write(t, ".engine/work/handoff-U1-1.json", "{not json")
            code, out = cli(t, "gate", "prepare", "unit=U1", "run=1")
            self.assertEqual(code, 2)
            self.assertEqual(out, ["gate: COULD NOT RUN — no base= given and no handoff at .engine/work/handoff-U1-1.json; run `handoff` first"])
            code, out = cli(t, "gate", "prepare", "unit=U1", "run=1", "base=nope")
            self.assertEqual((code, out), (2, ["gate: COULD NOT RUN — base/head do not resolve to commits"]))

    def test_prepare_quality_gate_failed(self):
        with tree() as t:
            write_config(t)
            git_repo(t)
            head = commit(t, "base")
            with mock.patch.object(gate, "prepare", return_value=([Out(["[tests] FAILED"], failed=True)], [], {})):
                code, out = cli(t, "gate", "prepare", "unit=U1", "run=1", f"base={head}")
            self.assertEqual(code, 1)
            self.assertEqual(out[1], "  [tests] FAILED")
            self.assertTrue(out[-1].startswith("gate: quality gate FAILED; the security gate does not run"), out)

    def test_submit_paths(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "gate", "submit", "unit=U1", "run=1")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("gate: COULD NOT RUN — verdict file unreadable"), out)
            v = write(t, "v.json", json.dumps({"verdict": "pass"}))
            with mock.patch.object(gate, "submit", return_value=("", ["verdict lacks findings"])) as s:
                code, out = cli(t, "gate", "submit", "unit=U1", "run=1", f"file={v}", "attested_by=Casey")
            self.assertEqual((code, out), (1, ["gate: verdict REFUSED", "  - verdict lacks findings"]))
            self.assertEqual(s.call_args[0][2:], ("U1", "1", {"verdict": "pass"}, "Casey"))
            with mock.patch.object(gate, "submit", return_value=("| U1 | 1 | pass |", [])):
                self.assertEqual(cli(t, "gate", "submit", "unit=U1", "run=1", f"file={v}"),
                                 (0, ["gate: recorded | U1 | 1 | pass |"]))

    def test_no_model_paths(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(gate, "no_model", return_value=("", ["no handoff", "no stamp"])):
                self.assertEqual(cli(t, "gate", "no-model", "unit=U1", "run=1"), (1, ["gate: REFUSED — no handoff; no stamp"]))
            with mock.patch.object(gate, "no_model", return_value=("ROW", [])):
                self.assertEqual(cli(t, "gate", "no-model", "unit=U1", "run=1", "attested_by=Casey"),
                                 (0, ["gate: recorded advisory row (no model; checklist not applied): ROW"]))


class Review(unittest.TestCase):
    def test_reviewer_command_must_be_set_and_found(self):
        with tree() as t:
            write(t, ".engine/work/handoff-U1-1.md", "# handoff" + NL)
            env = {k: v for k, v in os.environ.items() if k != "ENGINE_REVIEWER_CMD"}
            with mock.patch.dict(os.environ, env, clear=True):
                code, out = cli(t, "review", "unit=U1", "run=1")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("review: COULD NOT RUN — ENGINE_REVIEWER_CMD is not set"), out)
            with mock.patch.dict(os.environ, {"ENGINE_REVIEWER_CMD": "no-such-reviewer-xyz --flag"}):
                code, out = cli(t, "review", "unit=U1", "run=1")
            self.assertEqual((code, out), (2, ["review: COULD NOT RUN — reviewer 'no-such-reviewer-xyz' is not on the search path"]))


class Scan(unittest.TestCase):
    def test_happy_path_with_alarm(self):
        with tree() as t:
            write_config(t, operator="Casey")
            p, sc = fake_scan()
            with p, mock.patch.object(alarm, "raise_alarms", return_value=["F-1"]), \
                    mock.patch.object(alarm, "intervals", return_value=[("F-1", "2026-09-01", "", 2), ("F-0", "2026-08-01", "2026-08-03", 2)]):
                code, out = cli(t, "scan", "--alarm", "--skip-build")
            self.assertEqual(code, 1, "a red verdict exits 1")
            self.assertEqual(sc.run.call_args.kwargs, {"allow_unverified": False, "skip_build": True})
            self.assertEqual(out[0], "scan: engine=docker; mode=local; scanners ran: sast, sca; detection data 3 day(s) old")
            self.assertEqual(out[1:7], ["  - one problem", "  actionable: F-1 high", "  carried: F-2 low",
                                        "  closed: F-3 (no longer reported by a complete scan; plan-of-action history appended)",
                                        "  aged: F-4 past review-by",
                                        "scan: standing alarm RAISED; 1 new finding(s) recorded with owner, triage window and work item"])
            self.assertEqual(out[7:9], ["  F-1: detected 2026-09-01, open, 2 day(s)", "  F-0: detected 2026-08-01, resolved 2026-08-03, 2 day(s)"])
            self.assertEqual(out[-1], "scan: gate verdict RED for aaaaaaaaaaaa; stamp written")

    def test_verdict_exit_codes(self):
        with tree() as t:
            write_config(t)
            for verdict, want in (("green", 0), ("unverified", 3)):
                p, _ = fake_scan(scan_result(verdict=verdict, ran=[], data_age=None, problems=[], actionable=[],
                                             carried=[], closed=[], aged=[]))
                with p:
                    code, out = cli(t, "scan", "--allow-unverified")
                self.assertEqual(code, want)
                self.assertEqual(out[0], "scan: engine=docker; mode=local; scanners ran: none")

    def test_scan_error_could_not_run(self):
        with tree() as t:
            write_config(t)
            p, _ = fake_scan(error=runner.ScanError("no container engine"))
            with p:
                self.assertEqual(cli(t, "scan"), (2, ["scan: COULD NOT RUN — no container engine"]))

    def test_disconnected_mode_needs_images_present(self):
        with tree() as t:
            write_config(t, mode="disconnected")
            with mock.patch.object(bundles, "images_present", return_value=["sast: img is not present locally"]):
                code, out = cli(t, "scan")
            self.assertEqual((code, out), (2, ["scan: COULD NOT RUN — disconnected mode uses only images already present:",
                                               "  - sast: img is not present locally"]))

    def test_bundles_and_resolve(self):
        data = {"bundle_id": "B-1", "produced": "2026-10-01", "operator": "Casey", "source_side": "low"}
        with tree() as t:
            write_config(t)
            with mock.patch.object(bundles, "bundle_images", return_value=data) as bi, \
                    mock.patch.object(bundles, "bundle_data", return_value=data), \
                    mock.patch.object(bundles, "ingest", return_value=data) as ing:
                self.assertEqual(cli(t, "scan", "bundle-images", "d", "operator=Casey"),
                                 (0, ["scan: bundle-images: B-1 produced 2026-10-01 by Casey on side low"]))
                self.assertEqual(bi.call_args[0][3], "Casey")
                self.assertEqual(cli(t, "scan", "bundle-data", "d")[0], 0)
                self.assertEqual(cli(t, "scan", "ingest-data", "d", "--filtered-understood", "proxy strips")[0], 0)
                self.assertEqual(ing.call_args.kwargs, {"filtered_understood": "proxy strips"})
                self.assertEqual(cli(t, "scan", "ingest-images", "d")[0], 0)
                self.assertEqual(ing.call_args.kwargs, {"filtered_understood": ""})
            self.assertEqual(cli(t, "scan", "bundle-images"), (2, ["scan: COULD NOT RUN — list index out of range"]))
            with mock.patch.object(alarm, "resolve", return_value={"status": "fixed", "status_history": "open>fixed"}):
                self.assertEqual(cli(t, "scan", "resolve", "id=F-1", "status=fixed"),
                                 (0, ["scan: F-1 -> fixed; history: open>fixed"]))
            self.assertEqual(cli(t, "scan", "resolve", "status=fixed"), (2, ["scan: COULD NOT RUN — 'id'"]))


class Catalogue(unittest.TestCase):
    def test_usage_unknown_and_refused(self):
        with tree() as t:
            code, out = cli(t, "catalogue")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("catalogue ingest FILE"), out)
            self.assertEqual(cli(t, "catalogue", "bogus"), (2, ["catalogue: unknown subcommand 'bogus'"]))
            self.assertEqual(cli(t, "catalogue", "ingest"), (1, ["catalogue: REFUSED — list index out of range"]))

    def test_list_ingest_bundle(self):
        cat = {"_provenance": {"version": "5.1", "source": "nist", "retrieved": "2026-09-01", "redistribution": "public"},
               "entries": [1, 2]}
        with tree() as t:
            with mock.patch.object(catalogue, "load_all", return_value={"800-53": cat}):
                self.assertEqual(cli(t, "catalogue", "list"),
                                 (0, ["800-53: 5.1; 2 entries; source nist; retrieved 2026-09-01; public"]))
            with mock.patch.object(catalogue, "ingest", return_value=["+ AC-1"]) as ing:
                self.assertEqual(cli(t, "catalogue", "ingest", "f.json", "--acknowledge-markings"),
                                 (0, ["catalogue: adopted f.json; 1 change(s) against the previous version:", "  + AC-1"]))
            self.assertEqual(ing.call_args.kwargs, {"acknowledge_markings": True})
            with mock.patch.object(catalogue, "bundle", return_value={"produced": "today", "catalogues": [1], "sha256": "ab" * 32}):
                self.assertEqual(cli(t, "catalogue", "bundle", "d"),
                                 (0, ["catalogue: bundle produced today with 1 catalogue(s); sha256 abababababab…"]))
            with mock.patch.object(catalogue, "ingest_bundle", return_value={"800-53": ["- AC-2"]}):
                self.assertEqual(cli(t, "catalogue", "ingest-bundle", "d"), (0, ["catalogue: 800-53: 1 change(s)", "  - AC-2"]))


class Governance(unittest.TestCase):
    def test_show_propose_record_usage(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(governance, "governed_set", return_value=["AGENTS.md"]), \
                    mock.patch.object(governance, "zones", return_value=[{"file": "AGENTS.md", "section": "## Project rules"}]), \
                    mock.patch.object(governance, "staged_problems", return_value=["AGENTS.md staged without a row"]):
                self.assertEqual(cli(t, "governance", "show"), (0, [
                    "governed set (human-authored only, except allowlisted zones):", "  AGENTS.md",
                    "agent-editable zones (append grounded entries only):", "  AGENTS.md ## Project rules",
                    "staged: AGENTS.md staged without a row"]))
                with mock.patch.object(governance, "staged_diff", return_value="  "):
                    self.assertEqual(cli(t, "governance", "propose"), (1, ["governance: no governed file is staged"]))
                    self.assertEqual(cli(t, "governance", "record", "change_id=C1"), (1, ["governance: REFUSED — missing 'file_section'"]))
                with mock.patch.object(governance, "staged_diff", return_value="+ a rule"):
                    code, out = cli(t, "governance", "propose")
                    self.assertEqual(code, 0)
                    self.assertEqual(out[1], "+ a rule")
                    with mock.patch.object(governance, "record", return_value="GOV ROW") as rec:
                        self.assertEqual(cli(t, "governance", "record", "change_id=C1", "file_section=f", "grounding=g", "approved_by=a"),
                                         (0, ["governance: row written before the commit: GOV ROW"]))
                    self.assertEqual(rec.call_args.kwargs["shown_text"], "+ a rule")
                    with mock.patch.object(governance, "record", side_effect=RuntimeError("records unwritable")):
                        self.assertEqual(cli(t, "governance", "record", "change_id=C1", "file_section=f", "grounding=g", "approved_by=a"),
                                         (1, ["governance: REFUSED — records unwritable"]))
            code, out = cli(t, "governance")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("governance show | propose"), out)

    def test_disposition_usage_and_refusal(self):
        with tree() as t:
            code, out = cli(t, "disposition")
            self.assertEqual((code, out), (2, ["disposition checklist-line file= section= text= source="]))
            code, out = cli(t, "disposition", "checklist-line", "text=x")
            self.assertEqual((code, out), (1, ["disposition: REFUSED — 'source'"]))


class Probes(unittest.TestCase):
    def test_probe_needs_a_commit_then_runs(self):
        from engine import probes
        with tree() as t:
            write_config(t)
            git_repo(t)
            self.assertEqual(cli(t, "probe"), (2, ["probe: COULD NOT RUN — no commit"]))
            head = commit(t, "base")
            with mock.patch.object(probes, "run_probe", return_value=Out(["[probe] DELTA"], exit_code=1)) as rp:
                self.assertEqual(cli(t, "probe", "test_result=12 passed"), (1, ["[probe] DELTA"]))
            self.assertEqual(rp.call_args[0][2:], (head, "12 passed"))

    def test_inventory_undeclared_truth(self):
        from engine import probes, truth
        with tree() as t:
            with mock.patch.object(probes, "write_inventory", return_value=([], {"assessed": 2, "never": 1, "elsewhere": 0})) as wi:
                code, out = cli(t, "inventory")
            self.assertIsNone(wi.call_args[0][1], "an unconfigured tree is inventoried without a configuration")
            self.assertEqual((code, out), (0, [f"inventory: 2 assessed, 1 never assessed, 0 assessed elsewhere (evidence not available) -> {probes.INVENTORY}"]))
            with mock.patch.object(probes, "completeness_probe", return_value=Out(["[undeclared] 1 found"], exit_code=1)):
                self.assertEqual(cli(t, "undeclared"), (0, ["[undeclared] 1 found"]), "the probe reports; it never blocks")
            with mock.patch.object(truth, "check", return_value=Out(["[truth] DRIFT"], exit_code=1)):
                self.assertEqual(cli(t, "truth"), (1, ["[truth] DRIFT"]))


class Field(unittest.TestCase):
    def test_usage_and_unknown(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "field")
            self.assertEqual(code, 2)
            self.assertEqual(len(out), 4)
            self.assertTrue(out[0].startswith("field declare by=<name>"), out)
            self.assertEqual(cli(t, "field", "bogus"), (2, ["field: unknown subcommand"]))
            self.assertEqual(cli(t, "field", "declare", "budget=abc"),
                             (2, ["field: REFUSED — invalid literal for int() with base 10: 'abc'"]))

    def test_run_with_unresolvable_base_and_answers(self):
        doc = {"boundary": "FIELD RUN — bounded", "elapsed_seconds": 4, "budget_seconds": 60,
               "checks_deferred": ["scanner-pins"], "could_not_run": [], "verdict": "field-pass"}
        with tree() as t:
            write_config(t)
            git_repo(t)
            self.assertEqual(cli(t, "field", "run", "unit=U1", "run=1", "base=nope"),
                             (2, ["field: COULD NOT RUN — base/head do not resolve to commits"]))
            head = commit(t, "base")
            answers = write(t, "answers.json", json.dumps({"q1": "yes"}))
            with mock.patch.object(field, "run", return_value=(doc, "ROW", [Out(["[credential-scan] CLEAN"])])) as fr:
                code, out = cli(t, "field", "run", "unit=U1", "run=1", f"base={head}", "attested_by=Casey", f"answers={answers}")
            self.assertEqual(code, 3, "deferred checks exit 3")
            self.assertEqual(fr.call_args.kwargs["checklist_answers"], {"q1": "yes"})
            self.assertEqual(out, ["FIELD RUN — bounded", "  [credential-scan] CLEAN",
                                   "field: elapsed 4s of 60s budget; deferred: scanner-pins; could not run: none",
                                   "field: FIELD-PASS — row: ROW"])
            doc.update(verdict="field-fail", checks_deferred=[])
            with mock.patch.object(field, "run", return_value=(doc, "ROW", [])):
                self.assertEqual(cli(t, "field", "run", "unit=U1", "run=1", f"base={head}")[0], 1)
            doc.update(verdict="field-pass")
            with mock.patch.object(field, "run", return_value=(doc, "ROW", [])):
                self.assertEqual(cli(t, "field", "run", "unit=U1", "run=1", f"base={head}")[0], 0)

    def test_clear_status_models(self):
        with tree() as t:
            write_config(t)
            with mock.patch.object(field, "open_obligations", return_value=[
                    {"id": "OB-U1-1", "opened": "2026-09-01", "unit": "U1", "range": "a..b", "deferred_checks": "scanner-pins"}]):
                self.assertEqual(cli(t, "field", "clear"),
                                 (0, ["field: declaration removed; 1 reconciliation obligation(s) remain open — clearing discharges nothing"]))
                with mock.patch.object(field, "report", return_value=(["[field] 1 open"], 1, True)), \
                        mock.patch.object(field, "declaration", return_value={"declared_by": "Casey", "reason": "outage"}):
                    self.assertEqual(cli(t, "field", "status"), (1, [
                        "field mode: DECLARED by Casey (outage)", "[field] 1 open",
                        "  OB-U1-1 opened 2026-09-01 unit U1 range a..b: owed scanner-pins"]))
            self.assertEqual(cli(t, "field", "models"),
                             (0, ["no pinned models; the harness runs with no model at all (REQ-8.1)"]))
            pin = {"id": "gemma", "version": "3", "parameters": "4B", "sha256": "c" * 64, "_present": False, "source": "hf"}
            with mock.patch.object(field, "models", return_value={"gemma": pin}):
                self.assertEqual(cli(t, "field", "models"),
                                 (0, ["gemma 3 (4B) sha256:cccccccccccc weights not on disk — hf"]))


class Export(unittest.TestCase):
    def test_usage_unknown_verify_failure(self):
        from engine import export
        with tree() as t:
            code, out = cli(t, "export")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("export package"), out)
            with mock.patch.object(export, "verify", return_value=(False, ["index.html: hash mismatch"])) as v:
                self.assertEqual(cli(t, "export", "verify"),
                                 (1, ["  index.html: hash mismatch", "export: INTEGRITY FAILURE — 1 problem(s)"]))
            self.assertEqual(v.call_args[0], (".",))
            write_config(t)
            self.assertEqual(cli(t, "export", "bogus"), (2, ["export: unknown subcommand"]))
            self.assertEqual(cli(t, "export", "scan"), (2, ["export: REFUSED — 'out'"]))

    def test_package_incomplete_scan_disclosure(self):
        from engine import export
        with tree() as t:
            write_config(t)
            with mock.patch.object(export, "package", return_value=(t / "x", {"commit": "abc", "files": [1, 2], "marking": "",
                                                                             "incomplete": ["no scan stamp"]})):
                code, out = cli(t, "export", "package", "marking=")
            self.assertEqual(code, 1)
            self.assertEqual(out[1:], ["export: commit abc; 2 artifact(s) hashed at export; marking: none", "  INCOMPLETE: no scan stamp"])
            with mock.patch.object(export, "scan_bundle", return_value={"files": [1], "redacted": False}) as sb:
                self.assertEqual(cli(t, "export", "scan", "out=o", "--raw"),
                                 (0, ["export: scan bundle of 1 file(s), RAW — not for crossing a boundary"]))
            self.assertEqual(sb.call_args.kwargs, {"redacted": False})
            with mock.patch.object(export, "disclosure", return_value="# Disclosure" + NL) as d:
                self.assertEqual(cli(t, "export", "disclosure"), (0, ["# Disclosure"]))
            self.assertEqual(d.call_args[0][2], "unknown", "outside a repository the commit is unknown")


class Topology(unittest.TestCase):
    def test_usage_authority_unknown(self):
        with tree() as t:
            code, out = cli(t, "topology")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("topology authority |"), out)
            write_config(t, topology="two-instance", side="low")
            code, out = cli(t, "topology", "authority")
            self.assertEqual(code, 0)
            self.assertEqual(out[0], "# Record authority (spec 04 §10.1)")
            self.assertIn("this instance: side 'low', topology 'two-instance'", out)
            self.assertEqual(cli(t, "topology", "bogus"), (2, ["topology: unknown subcommand"]))
            self.assertEqual(cli(t, "topology", "drop"), (2, ["topology: REFUSED — 'out'"]))

    def test_drop_receive_change_status(self):
        from engine import topology
        with tree() as t:
            write_config(t, topology="two-instance", side="high")
            with mock.patch.object(topology, "source_drop", return_value={"bundle_id": "D-1", "revision": "b" * 40, "files": [1, 2],
                                                                          "records_transferred": False}) as sd:
                self.assertEqual(cli(t, "topology", "drop", "out=o", "operator=Casey", "--no-records"),
                                 (0, ["topology: drop D-1 at bbbbbbbbbbbb: 2 file(s); records NOT included"]))
            self.assertEqual(sd.call_args.kwargs, {"include_records": False})
            with mock.patch.object(topology, "receive_drop", return_value={"bundle_id": "D-1", "source_side": "low", "files": [1]}):
                code, out = cli(t, "topology", "receive", "dir=d", "operator=Casey")
            self.assertEqual(code, 0)
            self.assertTrue(out[0].startswith("topology: received D-1 from side low (1 file(s)); ingest recorded"), out)
            with mock.patch.object(topology, "record_change", return_value="CHG ROW"):
                self.assertEqual(cli(t, "topology", "change", "commit=abc", "what=w"), (0, ["topology: recorded — CHG ROW"]))
            with mock.patch.object(topology, "record_change", side_effect=topology.TopologyError("backport status required")):
                self.assertEqual(cli(t, "topology", "change", "commit=abc"), (2, ["topology: REFUSED — backport status required"]))
            with mock.patch.object(topology, "report", return_value=["[topology] two-instance"]), \
                    mock.patch.object(topology, "unported", return_value=[{"commit": "abc", "date": "2026-09-01T10:00",
                                                                           "what": "hotfix", "backport_status": "not yet ported"}]):
                self.assertEqual(cli(t, "topology", "status"),
                                 (0, ["[topology] two-instance", "  abc 2026-09-01 hotfix — not yet ported"]))


class Lifecycle(unittest.TestCase):
    def test_items(self):
        with tree() as t:
            code, out = cli(t, "item")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("item new id=<id>"), out)
            self.assertEqual(cli(t, "item", "bogus"), (2, ["item: unknown subcommand 'bogus'"]))
            self.assertEqual(cli(t, "item", "new", "id=I-1", "unit=U1", "done_when=the list page shows ten rows"),
                             (0, ["item: created tickets/I-1.md"]))
            self.assertEqual(cli(t, "item", "new", "id=I-2", "unit=U1", "done_when=the export verifies", "depends_on=I-1"),
                             (0, ["item: created tickets/I-2.md"]))
            code, out = cli(t, "item", "claim", "id=I-2")
            self.assertEqual(code, 1)
            self.assertEqual(out, ["item: REFUSED — I-2 is blocked by: I-1 (open)"])
            self.assertEqual(cli(t, "item", "claim", "id=I-1"), (0, ["item: I-1 -> claimed"]))
            self.assertEqual(cli(t, "item", "review", "id=I-1"), (0, ["item: I-1 -> in review"]))
            self.assertEqual(cli(t, "item", "done", "id=I-1"), (0, ["item: I-1 -> done"]))
            self.assertEqual(cli(t, "item", "done"), (1, ["item: REFUSED — 'id'"]))

    def test_units(self):
        with tree() as t:
            self.assertEqual(cli(t, "unit"), (2, ["unit new|building|review|merged id=<unit>"]))
            self.assertEqual(cli(t, "unit", "new", "id=U1"), (0, ["unit: created plans/units/U1.md"]))
            self.assertEqual(cli(t, "unit", "new", "id=U1"), (1, ["unit: REFUSED — U1 already exists"]))
            self.assertEqual(cli(t, "unit", "review", "id=U1"), (1, ["unit: REFUSED — U1: planned -> in review is not the next state"]))
            for sub, state in (("building", "building"), ("review", "in review"), ("merged", "merged")):
                self.assertEqual(cli(t, "unit", sub, "id=U1"), (0, [f"unit: U1 -> {state}"]))

    def test_status_without_configuration_exits_zero(self):
        with tree() as t:
            code, out = cli(t, "status")
            self.assertEqual(code, 0)
            self.assertTrue(out, "orientation always names a position")


class SelftestRunner(unittest.TestCase):
    def _case(self, outcome):
        class T(unittest.TestCase):
            def runTest(self):
                if outcome == "fail":
                    self.fail("boom")
                if outcome == "skip":
                    self.skipTest("later")
        return T()

    def test_reverse_order_and_failure_report(self):
        suite = unittest.TestSuite([unittest.TestSuite([self._case("pass"), self._case("skip")]), self._case("fail")])
        with tree() as t, mock.patch.object(cli_main, "discover_selftests", return_value=suite):
            import contextlib, io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                st = cli_main.run_selftests(t, reverse=True)
        self.assertEqual(st, {"pass": 1, "fail": 1, "skip": 1, "skips": ["runTest"]})
        self.assertIn("[selftest] FAIL: ", buf.getvalue())
        self.assertIn("AssertionError: boom", buf.getvalue())

    def test_no_suite_counts_nothing(self):
        with tree() as t, mock.patch.object(cli_main, "discover_selftests", return_value=None):
            self.assertEqual(cli_main.run_selftests(t), {"pass": 0, "fail": 0, "skip": 0, "skips": []})

    def test_placed_suite_runs_in_its_own_process(self):
        import contextlib, io, subprocess
        env = {k: v for k, v in os.environ.items() if k != cli_main.NESTING_GUARD}
        with tree() as t:
            (t / ".engine/harness/selftest").mkdir(parents=True)
            report = {"pass": 5, "fail": 0, "skip": 1, "skips": ["x"]}
            done = subprocess.CompletedProcess([], 0, stdout="[selftest] note" + NL + json.dumps(report) + NL, stderr="")
            buf = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(subprocess, "run", return_value=done) as run, \
                    contextlib.redirect_stdout(buf):
                st = cli_main.run_selftests(t, reverse=True)
            self.assertEqual(st, report)
            self.assertEqual(buf.getvalue(), "[selftest] note" + NL)
            self.assertEqual(run.call_args.kwargs["env"][cli_main.NESTING_GUARD], "1")
            self.assertIn("reverse=True", run.call_args[0][0][2])
            broken = subprocess.CompletedProcess([], 1, stdout="", stderr="Traceback: ImportError")
            buf = io.StringIO()
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(subprocess, "run", return_value=broken), \
                    contextlib.redirect_stdout(buf):
                st = cli_main.run_selftests(t)
            self.assertEqual(st, {"pass": 0, "fail": 1, "skip": 0, "skips": []})
            self.assertIn("[selftest] COULD NOT RUN: the placed suite did not report (exit 1): Traceback: ImportError", buf.getvalue())
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {cli_main.NESTING_GUARD: "1"}), contextlib.redirect_stdout(buf):
                st = cli_main.run_selftests(t)
            self.assertEqual(st["pass"] + st["fail"], 0)
            self.assertTrue(buf.getvalue().startswith("[selftest] COULD NOT RUN: a placed suite does not run"), buf.getvalue())


if __name__ == "__main__":
    unittest.main()
