# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Field mode (spec 11): a bounded gate that incurs a recorded, countable, aged debt."""
import hashlib
import json
import shutil
import unittest

from engine import field, gate
from engine.checks import reconciliation
from engine.outcome import State
from engine.records import gatelog, table
from .helpers import ROOT, cli, commit, find_line, tree, write
from .test_gate import cfg, feature, project as gate_project

NL = chr(10)
KEY = "AKIA" + "ABCDEFGHIJKLMNOP"   # assembled so this file does not itself trip the scan


def project(t, **over):
    """The gate fixture plus the vendored catalogues the floor's citation check resolves against."""
    base = gate_project(t, **over)
    shutil.copytree(ROOT / "engine" / "data" / "catalogues", t / ".engine" / "catalogues")
    return base


def declare(t, **over):
    kw = {"by": "Casey", "reason": "outage at the edge", "impossible": "no reachback, one operator", "budget_seconds": 600}
    kw.update(over)
    return field.declare(t, cfg(), **kw)


def fake_clock(steps):
    """A clock that advances by the given amounts on successive reads."""
    it = iter(steps)
    state = {"t": 0.0}

    def clock():
        state["t"] += next(it, 0)
        return state["t"]
    return clock


def open_rows(t):
    return field.open_obligations(t)


class Entry(unittest.TestCase):
    def test_never_inferred_run_without_declaration_refused(self):
        with tree() as t:
            base = project(t); head = feature(t)
            with self.assertRaises(field.FieldError) as cm:
                field.run(t, cfg(), "U1", 1, base, head, "Casey")
            self.assertIn("never inferred", str(cm.exception))

    def test_declaration_records_who_when_why_and_impossibility(self):
        with tree() as t:
            project(t)
            for missing in ("by", "reason", "impossible"):
                with self.assertRaises(field.FieldError):
                    declare(t, **{missing: "  "})
            d = declare(t)
            on_disk = json.loads((t / field.DECLARATION).read_text(encoding="utf-8"))
            self.assertEqual(on_disk["declared_by"], "Casey")
            self.assertEqual(on_disk["reason"], "outage at the edge")
            self.assertTrue(on_disk["declared_at"].startswith("20"))
            self.assertEqual(d["budget_seconds"], 600)

    def test_cannot_enter_to_escape_a_failing_check(self):
        with tree() as t:
            project(t)
            write(t, field.LAST_CHECK, json.dumps({"coverage-range": {"state": "checked-findings", "blocking": True}}))
            with self.assertRaises(field.FieldError) as cm:
                declare(t)
            self.assertIn("cannot be entered to escape a failing check", str(cm.exception))
            self.assertIn("coverage-range", str(cm.exception))
            # a failing floor check is not an escape — the floor runs regardless — and a clean state is fine
            write(t, field.LAST_CHECK, json.dumps({"coverage-range": {"state": "checked-clean", "blocking": False}}))
            declare(t)

    def test_clearing_the_declaration_discharges_nothing(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=1)
            field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 5]))
            self.assertEqual(len(open_rows(t)), 1)
            remaining = field.clear(t)
            self.assertEqual(remaining, 1)
            self.assertFalse((t / field.DECLARATION).exists())
            self.assertEqual(len(open_rows(t)), 1)


class Floor(unittest.TestCase):
    def test_floor_runs_even_with_zero_budget(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1, 1, 1, 1, 1, 1, 1, 1, 1]))
            ran = [n for n, _ in doc["checks_run"]]
            for name, _ in field.FLOOR:
                self.assertIn(name, ran)
            self.assertNotIn("credential-scan", doc["checks_deferred"])
            # everything deferrable was deferred by name, none silently
            for name, _ in field.DEFERRABLE:
                self.assertIn(name, doc["checks_deferred"])

    def test_floor_failure_is_a_field_fail_not_a_deferral(self):
        with tree() as t:
            base = project(t)
            head = feature(t, files={"src/app.py": "AWS_ACCESS_KEY_ID = '" + KEY + "'" + NL})
            declare(t, budget_seconds=0)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            self.assertEqual(doc["verdict"], "field-fail")
            self.assertIn("| field-fail |", line)
            self.assertIn("credential-scan", line)

    def test_could_not_run_is_distinct_from_deferred_and_fails(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=600)
            original = field.DEFERRABLE
            from engine.outcome import Outcome
            field.DEFERRABLE = [("findings-register", lambda r, c: Outcome.could_not_run("findings-register", "record unreadable"))] + original[1:]
            try:
                doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0]))
            finally:
                field.DEFERRABLE = original
            self.assertIn("findings-register", doc["could_not_run"])
            self.assertNotIn("findings-register", doc["checks_deferred"])
            self.assertEqual(doc["verdict"], "field-fail")


class Budget(unittest.TestCase):
    def test_budget_orders_and_defers_by_name_with_reason(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=10)
            # the floor reads no clock; findings-register (t=1) and scanner-pins (t=2) run, then the budget is gone (t=22)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1, 1, 20]))
            ran = [n for n, _ in doc["checks_run"]]
            self.assertIn("findings-register", ran)
            self.assertIn("scanner-pins", ran)
            self.assertIn("attack-surface", doc["checks_deferred"])
            self.assertIn("attack-surface", doc["did_not_run_in_time"])
            deferred = [o for o in outs if o.state is State.DEFERRED and o.check == "attack-surface"]
            self.assertEqual(len(deferred), 1)
            self.assertEqual(deferred[0].reason, "budget")
            self.assertIn("DEFERRED", deferred[0].line())
            self.assertFalse(doc["completed_within_budget"])
            self.assertIn("budget exhausted", field.render(doc, outs))

    def test_deferred_never_reported_as_passed_skipped_or_na(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            for o in outs:
                if o.check in doc["checks_deferred"]:
                    self.assertIs(o.state, State.DEFERRED)
                    self.assertNotIn("CLEAN", o.line())
                    self.assertNotIn("NOT APPLICABLE", o.line())
                    self.assertNotIn("skipped", o.line().lower())
            self.assertNotIn("| pass |", line)

    def test_elapsed_and_deferred_reported_at_end(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=600)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 2, 2, 2]))
            self.assertEqual(doc["budget_seconds"], 600)
            self.assertGreater(doc["elapsed_seconds"], 0)
            text = field.render(doc, outs)
            self.assertIn("elapsed:", text)
            self.assertIn("## Checks deferred (owed)", text)


class Verdict(unittest.TestCase):
    def test_field_row_in_ordinary_gate_log_with_distinct_class(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            rows, probs = gatelog.series(t)
            self.assertEqual(probs, [])
            self.assertEqual(len(rows), 1)
            r = rows[0]
            self.assertEqual(r["mode"], "field")
            self.assertEqual(r["verdict"], "field-pass")
            self.assertEqual(r["range"], f"{base[:12]}..{head[:12]}")
            self.assertEqual(r["obligation"], "OB-U1-1")
            self.assertIn("scan", r["deferred"])
            self.assertTrue(r["model"].startswith("none"))
            self.assertEqual(gatelog.unmatched_markers(t), [])       # the started marker was written and matched
            self.assertEqual(doc["separation_of_duties"], "not achieved")

    def test_boundary_sentence_at_top_of_verdict(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            text = (t / ".engine/local/field-verdict-U1-1.md").read_text(encoding="utf-8")
            self.assertEqual(text.splitlines()[2], doc["boundary"])
            self.assertIn("This is a FIELD verdict, not an ordinary gate pass", doc["boundary"])
            self.assertIn("separation of duties was not achieved", doc["boundary"])
            self.assertIn("declared by Casey because outage at the edge", doc["boundary"])
            for key in ("mode: field", "declared by Casey", "budget:", "reconciliation: open", "reviewer class:", "model:"):
                self.assertIn(key, text)

    def test_started_marker_written_before_any_check(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)

            def boom():
                raise RuntimeError("power loss")
            with self.assertRaises(RuntimeError):
                field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=boom)
            unmatched = gatelog.unmatched_markers(t)
            self.assertEqual(len(unmatched), 1)
            self.assertEqual(unmatched[0]["mode"], "field")

    def test_degradation_table_is_explicit_and_complete(self):
        keys = {a for a, _ in field.DEGRADATION_TABLE}
        for k in ("two-window isolation", "separation of duties", "control mutation", "failure semantics", "records", "full security checklist"):
            self.assertIn(k, keys)
        self.assertIn("retained", dict(field.DEGRADATION_TABLE)["two-window isolation"])
        self.assertIn("unchanged", dict(field.DEGRADATION_TABLE)["failure semantics"])
        self.assertIn("unchanged", dict(field.DEGRADATION_TABLE)["records"])
        with tree() as t:
            project(t)
            code, out = cli(t, "field", "table")
            self.assertEqual(code, 0)
            self.assertTrue(any(l.startswith("two-window isolation:") for l in out))


class Reconciliation(unittest.TestCase):
    def test_obligation_records_what_was_deferred_and_is_counted(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            rows = open_rows(t)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "OB-U1-1")
            self.assertIn("scan", rows[0]["deferred_checks"])
            self.assertIn("attack-surface", rows[0]["deferred_checks"])
            self.assertEqual(rows[0]["declared_by"], "Casey")
            lines, n, aged = field.report(t, cfg())
            self.assertEqual(n, 1)
            self.assertIn("reconciliation obligations open: 1 (OB-U1-1)", lines[0])

    def test_reconcile_requires_every_deferred_item_confirmed(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            owed = [x.strip() for x in open_rows(t)[0]["deferred_checks"].split(",")]
            partial = {x: True for x in owed[:-1]}
            with self.assertRaises(field.FieldError) as cm:
                field.reconcile(t, cfg(), "OB-U1-1", 2, "Casey", partial)
            self.assertIn("specifically confirm every deferred item", str(cm.exception))
            self.assertIn(owed[-1], str(cm.exception))
            self.assertEqual(len(open_rows(t)), 1)
            line = field.reconcile(t, cfg(), "OB-U1-1", 2, "Casey", {x: True for x in owed})
            self.assertEqual(open_rows(t), [])
            rows, _ = gatelog.series(t)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["verdict"], "pass")
            self.assertEqual(rows[1]["mode"], "normal")
            self.assertIn("discharges OB-U1-1 (field run U1#1)", rows[1]["tickets"])
            self.assertEqual(rows[1]["obligation"], "OB-U1-1")
            with self.assertRaises(field.FieldError):
                field.reconcile(t, cfg(), "OB-U1-1", 3, "Casey", {x: True for x in owed})

    def test_open_count_reported_at_every_gate(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            outs, ctx = gate.security_mechanical(t, cfg(), base, head, "U2")
            rec = [o for o in outs if o.check == "reconciliation"]
            self.assertEqual(len(rec), 1)
            self.assertIn("reconciliation obligations open: 1 (OB-U1-1)", rec[0].line())

    def test_ceiling_requires_recorded_acceptance(self):
        with tree() as t:
            base = project(t); head = feature(t)
            for i in range(1, 3):
                declare(t, budget_seconds=0)
                field.run(t, cfg(), "U1", i, base, head, "Casey", clock=fake_clock([0, 1]))
            c = cfg(obligation_ceiling=2)
            with self.assertRaises(field.FieldError) as cm:
                field.declare(t, c, by="Casey", reason="r", impossible="i", budget_seconds=1)
            self.assertIn("at or above the ceiling of 2", str(cm.exception))
            d = field.declare(t, c, by="Casey", reason="r", impossible="i", budget_seconds=1, accept_over_ceiling="incident 44, accepted by Casey")
            self.assertEqual(d["over_ceiling_accepted"], "incident 44, accepted by Casey")
            self.assertEqual(d["open_obligations_at_entry"], 2)

    def test_aged_obligation_is_a_finding(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=0)
            field.run(t, cfg(), "U1", 1, base, head, "Casey", clock=fake_clock([0, 1]))
            o = reconciliation.run(t, cfg())
            self.assertIs(o.state, State.CLEAN)
            p = t / field.OBLIGATIONS
            text = p.read_text(encoding="utf-8")
            today = open_rows(t)[0]["opened"][:10]
            p.write_text(text.replace(today, "2020-01-01", 1), encoding="utf-8", newline="\n")
            o = reconciliation.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertIn("OB-U1-1 is", o.findings[0])
            self.assertIn("past the threshold", o.findings[0])
            self.assertIs(reconciliation.run(t, cfg(obligation_max_age_days=100000)).state, State.CLEAN)

    def test_reconciliation_check_states(self):
        with tree() as t:
            write(t, "x", "")
            self.assertIs(reconciliation.run(t, cfg()).state, State.NOTHING_YET)
            project(t)
            write(t, field.OBLIGATIONS, "| garbage" + NL)
            self.assertIs(reconciliation.run(t, cfg()).state, State.COULD_NOT_RUN)


class Model(unittest.TestCase):
    def test_no_model_configuration_is_supported(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=600)
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", model="none", clock=fake_clock([0]))
            self.assertIn("none — mechanical only", doc["model"])
            self.assertIn("| mechanical-only |", line)

    def test_unpinned_model_refused_pinned_model_recorded_with_scale(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=600)
            with self.assertRaises(field.FieldError) as cm:
                field.run(t, cfg(), "U1", 1, base, head, "Casey", model="tiny-llm", clock=fake_clock([0]))
            self.assertIn("not pinned", str(cm.exception))
            weights = b"not really weights"
            write(t, f"{field.MODELS_DIR}/tiny.bin", "")
            (t / field.MODELS_DIR / "tiny.bin").write_bytes(weights)
            prov = {"id": "tiny-llm", "file": "tiny.bin", "sha256": hashlib.sha256(weights).hexdigest(), "version": "1.2",
                    "parameters": "3B", "source": "vendor drop 2026-09"}
            write(t, f"{field.MODELS_DIR}/tiny-llm.provenance.json", json.dumps(prov))
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", model="tiny-llm", clock=fake_clock([0]))
            self.assertEqual(doc["model"], f"tiny-llm 1.2 (3B; sha256:{prov['sha256'][:12]})")
            self.assertIn("3B", line)
            # tampered weights are refused
            (t / field.MODELS_DIR / "tiny.bin").write_bytes(b"swapped")
            with self.assertRaises(field.FieldError) as cm:
                field.models(t)
            self.assertIn("do not match the pinned hash", str(cm.exception))
            prov.pop("parameters")
            write(t, f"{field.MODELS_DIR}/tiny-llm.provenance.json", json.dumps(prov))
            (t / field.MODELS_DIR / "tiny.bin").write_bytes(weights)
            with self.assertRaises(field.FieldError) as cm:
                field.models(t)
            self.assertIn("lacks parameters", str(cm.exception))

    def test_unreached_checklist_items_deferred_not_dropped(self):
        with tree() as t:
            base = project(t); head = feature(t)
            declare(t, budget_seconds=600)
            weights = b"w"
            (t / field.MODELS_DIR).mkdir(parents=True)
            (t / field.MODELS_DIR / "m.bin").write_bytes(weights)
            write(t, f"{field.MODELS_DIR}/m.provenance.json", json.dumps({"id": "m", "file": "m.bin", "sha256": hashlib.sha256(weights).hexdigest(),
                                                                          "version": "1", "parameters": "7B", "source": "s"}))
            answers = {"B1": "pass", "B2": "pass"}
            doc, line, outs = field.run(t, cfg(), "U1", 1, base, head, "Casey", model="m", checklist_answers=answers, clock=fake_clock([0]))
            item = [d for d in doc["checks_deferred"] if d.startswith("checklist:")]
            self.assertEqual(len(item), 1)
            self.assertIn("B3", item[0])
            self.assertNotIn("B1,", item[0] + ",")
            self.assertIn("checklist:", open_rows(t)[0]["deferred_checks"])
            # answers without a named reviewer are refused: say what the reviewer is
            with self.assertRaises(field.FieldError):
                field.run(t, cfg(), "U1", 2, base, head, "Casey", model="none", checklist_answers=answers, clock=fake_clock([0]))


class Cli(unittest.TestCase):
    def test_declare_run_status_reconcile_round_trip(self):
        with tree() as t:
            base = project(t); head = feature(t)
            code, out = cli(t, "field", "run", "unit=U1", "run=1", f"base={base}", "attested_by=Casey")
            self.assertEqual(code, 2)
            self.assertIn("never inferred", find_line(out, "field: REFUSED"))
            code, out = cli(t, "field", "declare", "by=Casey", "reason=edge outage", "impossible=no reachback", "budget=0")
            self.assertEqual(code, 0, out)
            code, out = cli(t, "field", "run", "unit=U1", "run=1", f"base={base}", "attested_by=Casey")
            self.assertEqual(code, 3, out)          # deferred: owed, not passed
            self.assertTrue(out[0].startswith("This is a FIELD verdict"))
            self.assertIn("FIELD-PASS", find_line(out, "field: FIELD-"))
            code, out = cli(t, "field", "status")
            self.assertEqual(code, 0)
            self.assertIn("open: 1", find_line(out, "reconciliation obligations"))
            owed = open_rows(t)[0]["deferred_checks"].replace(" ", "")
            code, out = cli(t, "field", "reconcile", "obligation=OB-U1-1", "run=2", "attested_by=Casey", f"confirmed={owed}")
            self.assertEqual(code, 0, out)
            self.assertEqual(open_rows(t), [])

    def test_check_records_last_state_for_entry_rule(self):
        with tree() as t:
            project(t)
            cli(t, "check")
            self.assertTrue((t / field.LAST_CHECK).is_file())
            data = json.loads((t / field.LAST_CHECK).read_text(encoding="utf-8"))
            self.assertIn("config", data)
