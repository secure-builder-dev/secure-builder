# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The record set (spec 02 §2–5, §10.3, §11; spec 01 §12)."""
import json
import unittest

from engine import distribute
from engine.checks import findings_register, record_integrity, record_schema, run_attestation
from engine.config import Config
from engine.outcome import State
from engine.records import changelog, findings, gatelog, table, templates
from engine.records import schema as sch
from .helpers import ROOT, cli, commit, find_line, git, git_repo, tree, write, write_config

CFG = Config({"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
              "side": "low", "timezone": "UTC"})
BASE, HEAD = "a" * 40, "b" * 40
RANGE = f"{BASE[:12]}..{HEAD[:12]}"


def seeded(t, **cfg):
    write_config(t, side="low", timezone="UTC", **cfg)
    templates.render_all(t / ".engine" / "records")
    write(t, ".engine/records/README.md", "# Records" + chr(10))
    return t


def row(t, unit="epic-1", run="1", verdict="pass", **over):
    kw = dict(unit=unit, range=RANGE, run=run, verdict=verdict, reviewer="security-gate", reviewer_class="automated",
              attested_by="Casey Houle", harness_version="0.1.0", checklist_version="c1")
    kw.update(over)
    return gatelog.append(t, CFG, **kw)


class Schema(unittest.TestCase):
    def test_defined_once_and_templates_match(self):
        with tree() as t:
            templates.render_all(t)
            for name, fn in templates.RENDERERS.items():
                self.assertEqual((ROOT / "engine/dist/templates/records" / name).read_text(encoding="utf-8"), fn(),
                                 f"dist template {name} is stale: regenerate from engine.records.schema")

    def test_gate_log_carries_every_required_field(self):
        cols = sch.GATE_LOG[2]
        for c in ("date", "unit", "range", "run", "mode", "verdict", "findings", "tickets", "reviewer", "reviewer_class",
                  "attested_by", "harness_version", "checklist_version", "side", "supersedes", "model"):
            self.assertIn(c, cols)

    def test_every_schema_carries_side(self):
        for name, s in sch.ALL.items():
            self.assertIn("side", s[2], name)


class Table(unittest.TestCase):
    def test_parse_rows_and_template_only(self):
        text = templates.gate_log()
        rows, problems, versions = table.parse(text, "gate-log")
        self.assertEqual((rows, problems, versions), ([], [], [1]))
        self.assertTrue(table.is_template_only(rows))

    def test_header_drift_is_a_problem(self):
        text = templates.gate_log().replace("| date | unit |", "| date | epic |")
        rows, problems, _ = table.parse(text, "gate-log")
        self.assertEqual(len(problems), 1)
        self.assertIn("does not match schema gate-log/1", problems[0])

    def test_malformed_row_reported_not_skipped(self):
        text = templates.gate_log() + "| only | three | cells |" + chr(10)
        rows, problems, _ = table.parse(text, "gate-log")
        self.assertEqual(rows, [])
        self.assertEqual(problems, ["line 13: row has 3 cells, schema gate-log/1 has 19"])

    def test_unknown_schema_version_reported(self):
        text = templates.gate_log().replace("Schema: gate-log/1.", "Schema: gate-log/7.")
        rows, problems, versions = table.parse(text, "gate-log")
        self.assertEqual(versions, [])
        self.assertIn("not a version this harness knows", problems[0])

    def test_append_requires_every_column_and_writes_unknown_for_blank(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                table.append(t, gatelog.FILE, sch.GATE_LOG, {"date": "x"})
            values = {c: "v" for c in sch.GATE_LOG[2]}
            values["model"] = ""
            line = table.append(t, gatelog.FILE, sch.GATE_LOG, values)
            self.assertIn("| unknown |", line)

    def test_append_refuses_to_create_a_record(self):
        with tree() as t:
            with self.assertRaises(table.Malformed):
                table.append(t, gatelog.FILE, sch.GATE_LOG, {c: "v" for c in sch.GATE_LOG[2]})


class GateLog(unittest.TestCase):
    def test_row_appended_with_timestamp_in_configured_timezone(self):
        with tree() as t:
            seeded(t)
            line = row(t)
            rows, problems = gatelog.series(t)
            self.assertEqual(problems, [])
            self.assertEqual(len(rows), 1)
            self.assertRegex(rows[0]["date"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
            self.assertEqual(rows[0]["date"][-6:], "+00:00")
            self.assertEqual(rows[0]["side"], "low")
            self.assertEqual(rows[0]["mode"], "normal")
            self.assertEqual(rows[0]["harness_version"], "0.1.0")

    def test_findings_column_carries_identifiers_not_only_a_count(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                row(t, findings="3")
            row(t, findings="3: F-21, F-22, F-23")
            self.assertEqual(gatelog.series(t)[0][0]["findings"], "3: F-21, F-22, F-23")

    def test_unresolvable_timezone_is_refused_not_defaulted(self):
        from engine import records
        with self.assertRaises(records.TimezoneUnavailable):
            records.now(Config({"timezone": "Nowhere/Invalid"}))

    def test_reruns_append_never_replace(self):
        with tree() as t:
            seeded(t)
            row(t, run="1", verdict="fail", findings="2: F-1, F-2")
            row(t, run="2", verdict="fail", findings="1: F-2")
            row(t, run="3", verdict="pass")
            rows, _ = gatelog.series(t)
            self.assertEqual([r["run"] for r in rows], ["1", "2", "3"])
            self.assertEqual([r["verdict"] for r in rows], ["fail", "fail", "pass"])

    def test_range_must_be_commits_not_branch_names(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                row(t, range="main..feature")

    def test_reviewer_class_and_attestation_required(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                row(t, reviewer_class="robot")
            with self.assertRaises(table.Malformed):
                row(t, attested_by="")

    def test_unknown_versions_written_as_unknown_not_blank(self):
        with tree() as t:
            seeded(t)
            line = gatelog.append(t, CFG, unit="u", range=RANGE, run="1", verdict="pass", reviewer="r",
                                  reviewer_class="human", attested_by="Casey")
            rows, _ = gatelog.series(t)
            self.assertEqual((rows[0]["harness_version"], rows[0]["checklist_version"]), ("unknown", "unknown"))
            self.assertNotIn("|  |", line)

    def test_field_row_is_a_distinct_class(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                row(t, mode="field", verdict="pass")
            with self.assertRaises(table.Malformed):
                row(t, mode="normal", verdict="field-pass")
            row(t, mode="field", verdict="field-pass", deferred="mutation,coverage", obligation="OB-1")
            rows, _ = gatelog.series(t)
            self.assertEqual((rows[0]["mode"], rows[0]["verdict"]), ("field", "field-pass"))

    def test_supersede_appends_and_marks_never_erases(self):
        with tree() as t:
            seeded(t)
            row(t, run="1", verdict="pass")
            gatelog.supersede(t, CFG, "epic-1", "1", "missed an unscoped query", "incident 7", "F-9 -> permanent check",
                              attested_by="Casey Houle", reviewer="Casey Houle")
            rows, _ = gatelog.series(t)
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0]["_superseded"])
            self.assertEqual(rows[1]["verdict"], "superseded")
            self.assertEqual(rows[1]["supersedes"], "epic-1#1")
            self.assertIn("wrong: missed an unscoped query", rows[1]["findings"])
            self.assertIn("disposition: F-9 -> permanent check", rows[1]["findings"])
            code, lines = cli(t, "records")
            self.assertTrue(any(l.endswith("[SUPERSEDED]") for l in lines), lines)

    def test_series_reads_rotated_and_per_run_files_as_one(self):
        with tree() as t:
            seeded(t)
            row(t, unit="old", run="1", date="2024-05-01T00:00:00+00:00")
            row(t, unit="new", run="1")
            n = gatelog.rotate(t, "2024")
            self.assertEqual(n, 1)
            self.assertTrue((t / ".engine/records/gate-log.2024.md").is_file())
            write(t, ".engine/records/gate-log/run-x.md", templates.gate_log() +
                  "| 2026-01-01T00:00:00+00:00 | per-run | " + RANGE + " | 1 | normal | pass | 0 | - | r | human | - | Casey | v | c | low | - | - | - | - |" + chr(10))
            rows, problems = gatelog.series(t)
            self.assertEqual(problems, [])
            self.assertEqual(sorted(r["unit"] for r in rows), ["new", "old", "per-run"])
            self.assertIn("gate-log.2024.md", (t / ".engine/records/README.md").read_text())

    def test_rotation_deletes_nothing(self):
        with tree() as t:
            seeded(t)
            row(t, unit="old", run="1", date="2024-05-01T00:00:00+00:00")
            before = [r["unit"] for r in gatelog.series(t)[0]]
            gatelog.rotate(t, "2024")
            self.assertEqual([r["unit"] for r in gatelog.series(t)[0]], before)


class StartedMarkers(unittest.TestCase):
    def test_marker_written_before_and_matched_by_row(self):
        with tree() as t:
            seeded(t)
            p = gatelog.write_started(t, CFG, "epic-1", "1", RANGE, HEAD)
            data = json.loads(p.read_text())
            self.assertEqual((data["unit"], data["run"], data["range"], data["head"], data["side"]), ("epic-1", "1", RANGE, HEAD, "low"))
            self.assertEqual(len(gatelog.unmatched_markers(t)), 1)
            row(t)
            self.assertEqual(gatelog.unmatched_markers(t), [])

    def test_run_number_used_once(self):
        with tree() as t:
            seeded(t)
            gatelog.write_started(t, CFG, "epic-1", "1", RANGE, HEAD)
            with self.assertRaises(table.Malformed):
                gatelog.write_started(t, CFG, "epic-1", "1", RANGE, HEAD)


class Findings(unittest.TestCase):
    def test_permanent_check_row_and_pointer_resolution(self):
        with tree() as t:
            seeded(t)
            write(t, "engine/checks/scope.py", "def run(): pass" + chr(10))
            findings.add_check(t, CFG, id="F-1", finding_class="a record-scoped query missing its ownership filter",
                               mechanism="scope-filter check", lives_in="engine/checks/scope.py#run", decided_by="Casey Houle")
            blocking, reported, _ = findings.problems(t)
            self.assertEqual((blocking, reported), ([], []))
            (t / "engine/checks/scope.py").write_text("def other(): pass" + chr(10))
            blocking, _, _ = findings.problems(t)
            self.assertEqual(blocking, ["F-1: mechanism 'scope-filter check' at 'engine/checks/scope.py#run' does not resolve — the check has regressed"])

    def test_row_must_name_a_human(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                findings.add_check(t, CFG, id="F-1", finding_class="c", mechanism="m", lives_in="x", decided_by="agent")

    def test_risk_needs_attack_path_and_accepted_needs_proof(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                findings.add_risk(t, CFG, id="R-1", risk="r", attack_path="-", compensating_control="c", proof="tests/x.py runs in CI",
                                  re_review_trigger="release", owner="o", review_by="2027-01-01", decided_by="Casey")
            with self.assertRaises(table.Malformed):
                findings.add_risk(t, CFG, id="R-1", risk="r", attack_path="attacker posts to /x", compensating_control="c",
                                  proof="will add a test", re_review_trigger="release", owner="o", review_by="2027-01-01",
                                  decided_by="Casey", status="accepted")
            findings.add_risk(t, CFG, id="R-1", risk="r", attack_path="attacker posts to /x", compensating_control="rate limit",
                              proof="tests/test_rate.py::test_limit runs in CI", re_review_trigger="release", owner="o",
                              review_by="2027-01-01", decided_by="Casey", status="accepted")
            blocking, reported, _ = findings.problems(t)
            self.assertEqual((blocking, reported), ([], []))

    def test_open_risk_without_proof_reported_every_run(self):
        with tree() as t:
            seeded(t)
            findings.add_risk(t, CFG, id="R-2", risk="r", attack_path="attacker replays token", compensating_control="nonce",
                              proof="planned", re_review_trigger="release", owner="o", review_by="2027-01-01", decided_by="Casey")
            for _ in range(2):
                blocking, reported, _ = findings.problems(t)
                self.assertEqual(reported, ["R-2: open — compensating control 'nonce' has no proof it exists"])

    def test_agent_cannot_accept_its_own_finding(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                findings.add_risk(t, CFG, id="R-3", risk="r", attack_path="x does y", compensating_control="c",
                                  proof="tests/t.py runs", re_review_trigger="r", owner="o", review_by="2027-01-01",
                                  decided_by="automated", status="accepted")


class Changelog(unittest.TestCase):
    def test_sign_off_must_record_what_was_shown(self):
        with tree() as t:
            seeded(t)
            with self.assertRaises(table.Malformed):
                changelog.add(t, CFG, change_id="G-1", file_section="RULES.md §2", base_commit="a" * 7, result_commit="pending",
                              grounding="spec 01 §11", sign_off="approved")
            changelog.add(t, CFG, change_id="G-1", file_section="RULES.md §2", base_commit="a" * 7, result_commit="pending",
                          grounding="spec 01 §11", sign_off="approved after being shown hunks 1-2 inline", retroactive=True,
                          rode_along="typo fix in §3, not authorized separately")
            rows, problems = changelog.read(t)
            self.assertEqual(problems, [])
            self.assertEqual((rows[0]["retroactive"], rows[0]["rode_along"][:8]), ("yes", "typo fix"))


class Checks(unittest.TestCase):
    def test_schema_check_catches_header_drift(self):
        with tree() as t:
            seeded(t)
            p = t / gatelog.FILE
            p.write_text(p.read_text().replace("| date | unit |", "| date | epic |"))
            o = record_schema.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith(".engine/records/gate-log.md [gate-log]: line"), o.findings)

    def test_schema_check_absent_record_is_a_finding(self):
        with tree() as t:
            seeded(t)
            (t / findings.FILE).unlink()
            o = record_schema.run(t, CFG)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith(".engine/records/findings-register.md: required record is absent"), o.findings)

    def test_schema_check_absent_non_load_bearing_record_opens_ticket_not_block(self):
        with tree() as t:
            seeded(t)
            (t / ".engine/records/carried-findings.md").unlink()
            o = record_schema.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertIn("open a ticket", o.findings[0])

    def test_schema_check_template_only_is_not_success(self):
        with tree() as t:
            seeded(t)
            o = record_schema.run(t, CFG)
            self.assertIs(o.state, State.NOTHING_YET)
            row(t)
            self.assertIs(record_schema.run(t, CFG).state, State.CLEAN)

    def test_integrity_check_catches_altered_row(self):
        with tree() as t:
            seeded(t); git_repo(t)
            row(t, run="1", verdict="fail")
            commit(t)
            p = t / gatelog.FILE
            p.write_text(p.read_text().replace("| fail |", "| pass |"))
            o = record_integrity.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith(".engine/records/gate-log.md: a previously committed row was altered or removed"), o.findings)

    def test_integrity_check_catches_deleted_marker(self):
        with tree() as t:
            seeded(t); git_repo(t)
            gatelog.write_started(t, CFG, "e", "1", RANGE, HEAD)
            commit(t)
            (t / gatelog.STARTED_DIR / "e-1.json").unlink()
            o = record_integrity.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertIn(".engine/records/started/e-1.json: started marker deleted — a marker is a record and is never removed", o.findings)

    def test_integrity_check_appended_row_is_clean(self):
        with tree() as t:
            seeded(t); git_repo(t)
            row(t, run="1", verdict="fail")
            commit(t)
            row(t, run="2", verdict="pass")
            self.assertIs(record_integrity.run(t, CFG).state, State.CLEAN)

    def test_attestation_marker_without_row_is_blocking(self):
        with tree() as t:
            seeded(t)
            gatelog.write_started(t, CFG, "epic-1", "1", RANGE, HEAD)
            o = run_attestation.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith("epic-1#1: started"), o.findings)
            self.assertTrue(o.findings[0].endswith("no completed row"))

    def test_attestation_row_without_marker_is_blocking(self):
        with tree() as t:
            seeded(t)
            row(t)
            o = run_attestation.run(t, CFG)
            self.assertEqual(o.findings, ["epic-1#1: gate-log row has no started marker — a row written with no run behind it"])

    def test_attestation_applies_unchanged_in_field_mode(self):
        with tree() as t:
            seeded(t)
            row(t, mode="field", verdict="field-pass", deferred="mutation", obligation="OB-1")
            o = run_attestation.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertEqual(o.findings, ["epic-1#1: gate-log row has no started marker — a row written with no run behind it"])

    def test_attestation_matched_is_clean(self):
        with tree() as t:
            seeded(t)
            gatelog.write_started(t, CFG, "epic-1", "1", RANGE, HEAD)
            row(t)
            self.assertIs(run_attestation.run(t, CFG).state, State.CLEAN)

    def test_findings_register_check_blocks_on_regressed_mechanism(self):
        with tree() as t:
            seeded(t)
            findings.add_check(t, CFG, id="F-1", finding_class="c", mechanism="m", lives_in="engine/gone.py", decided_by="Casey")
            o = findings_register.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)

    def test_findings_register_check_reports_unproven_risk_without_blocking(self):
        with tree() as t:
            seeded(t)
            findings.add_risk(t, CFG, id="R-2", risk="r", attack_path="x", compensating_control="c", proof="pending",
                              re_review_trigger="r", owner="o", review_by="2027-01-01", decided_by="Casey")
            o = findings_register.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)

    def test_findings_register_check_template_is_nothing_yet(self):
        with tree() as t:
            seeded(t)
            self.assertIs(findings_register.run(t, CFG).state, State.NOTHING_YET)


class Statements(unittest.TestCase):
    README = ROOT / "engine/dist/templates/records/README.md"

    def test_single_writer_assumption_and_clock_stated_where_operator_reads(self):
        lines = self.README.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len([l for l in lines if "Single-writer assumption" in l]), 1)
        self.assertEqual(len([l for l in lines if "keeping both" in l]), 1)
        self.assertEqual(len([l for l in lines if "`clock`" in l]), 1)

    def test_changelog_presented_as_configuration_change_control_record(self):
        lines = templates.governance_changelog().splitlines()
        self.assertTrue(any("configuration change" in l for l in lines))

    def test_deltas_presented_as_continuous_monitoring_record(self):
        lines = templates.standing_state_deltas().splitlines()
        self.assertTrue(any("continuous monitoring record" in l for l in lines))

    def test_one_name_one_artifact(self):
        import re
        withdrawn = re.compile(r"standing exceptions register|permanent record", re.I)
        for p in (ROOT / "engine").rglob("*.py"):
            self.assertIsNone(withdrawn.search(p.read_text(encoding="utf-8")), f"{p.name} uses a withdrawn name for the findings register")

    def test_gitignore_keeps_records_and_stamp_committed(self):
        with tree() as t:
            distribute.update(t)
            lines = (t / ".engine/.gitignore").read_text(encoding="utf-8").splitlines()
            self.assertIn("local/", lines)
            self.assertIn("scan/raw/", lines)
            self.assertFalse(any(l.strip().startswith("records") for l in lines))
            self.assertFalse(any(l.strip() in ("scan/", "scan") for l in lines), "the verdict stamp under scan/ is committed")


class Cli(unittest.TestCase):
    def test_record_commands(self):
        with tree() as t:
            seeded(t)
            code, lines = cli(t, "record", "started", "unit=e", "run=1", f"range={RANGE}", f"head={HEAD}")
            self.assertEqual(code, 0, lines)
            code, lines = cli(t, "record", "gate-log", "unit=e", f"range={RANGE}", "run=1", "verdict=pass",
                              "reviewer=sg", "reviewer_class=automated", "attested_by=Casey")
            self.assertEqual(code, 0, lines)
            code, lines = cli(t, "record", "gate-log", "unit=e", "range=main..HEAD", "run=2", "verdict=pass",
                              "reviewer=sg", "reviewer_class=automated", "attested_by=Casey")
            self.assertEqual(code, 1)
            self.assertTrue(lines[0].startswith("record: REFUSED"), lines)
            code, lines = cli(t, "records")
            find_line(lines, "records: gate log: 1 row(s)")
            self.assertIn("reviewer=sg (automated) attested_by=Casey", find_line(lines, "  20"))
            find_line(lines, "records: findings per gate run (spec 01 REQ-12.3, trend): e#1=0")
