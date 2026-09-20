# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Two-instance topology across a one-way boundary (spec 04 §10)."""
import json
import unittest

from engine import export, gate, probes, topology
from engine.checks import high_side_changes
from engine.config import Config
from engine.outcome import State
from engine.records import gatelog, table, templates
from .helpers import commit, git, git_repo, line_with, tree, write, write_config
from .test_gate import APP, AUTH, TEST

NL = chr(10)


def cfg(side, **over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local" if side == "low" else "disconnected",
         "protected_branch": "main", "topology": f"{side}-side", "side": side, "timezone": "UTC", "test_command": ["python", "-c", "pass"]}
    d.update(over)
    return Config(d)


def low_side(t):
    """A low-side instance with one gated unit of work merged to main."""
    write_config(t, topology="low-side", side="low", protected_branch="main", test_command=["python", "-c", "pass"])
    templates.render_all(t / ".engine/records")
    git_repo(t)
    write(t, "src/app.py", "app = object()" + NL)
    base = commit(t, "base")
    for f, text in {"src/app.py": APP, "src/auth.py": AUTH, "tests/test_items.py": TEST}.items():
        write(t, f, text)
    head = commit(t, "ABC-12 add items route")
    gatelog.append(t, cfg("low"), unit="U1", range=f"{base[:12]}..{head[:12]}", run="1", verdict="pass", reviewer="security-gate",
                   reviewer_class="automated-with-human-review", model="reviewer-x 70B", attested_by="Casey", harness_version="0.1.0", checklist_version="cl-abc")
    commit(t, "records")
    return base, head


def high_side(t):
    """An empty high-side instance: its own configuration, records and history; no view of the low side."""
    write_config(t, topology="high-side", side="high", mode="disconnected", protected_branch="main", test_command=["python", "-c", "pass"])
    templates.render_all(t / ".engine/records")
    git_repo(t)
    return commit(t, "high-side init")


class Authority(unittest.TestCase):
    def test_every_artifact_class_names_its_authoritative_side(self):
        classes = [a for a, _, _ in topology.AUTHORITY]
        for must in ("gate log", "findings register", "governance changelog", "scan artifacts and stamp", "ingest records", "high-side changes", "evidence export"):
            self.assertTrue(any(must in c for c in classes), must)
        self.assertEqual(dict((a, b) for a, b, _ in topology.AUTHORITY)["gate log"], topology.PRODUCING_SIDE)
        self.assertEqual(dict((a, b) for a, b, _ in topology.AUTHORITY)["evidence export"], "high side")
        text = topology.render_authority(cfg("high"))
        line_with(text, "| gate log | the side where the work happened |")
        line_with(text, "no requirement depends on the high->low path")

    def test_crossings_enumerated_and_nothing_required_returns(self):
        low_high = [k for k, _ in topology.CROSSINGS["low->high"]]
        for k in ("source", "catalogues", "detection-data", "scanner-images", "approved-dependencies"):
            self.assertIn(k, low_high)
        self.assertTrue(topology.permitted("source", "low", "high"))
        self.assertFalse(topology.permitted("source", "high", "low"))
        self.assertFalse(topology.permitted("records-sync", "low", "high"))
        for k, desc in topology.CROSSINGS["high->low"]:
            self.assertIn("nothing here requires it", desc)


class Drop(unittest.TestCase):
    def test_drop_carries_provenance_hashes_and_records(self):
        with tree() as t:
            base, head = low_side(t)
            d = topology.source_drop(t, t / "drop", cfg("low"), "Casey", revision="HEAD")
            for key in ("kind", "revision", "produced", "source_side", "operator", "archive_sha256", "bundle_id"):
                self.assertTrue(d[key], key)
            self.assertEqual(d["source_side"], "low")
            self.assertEqual(d["operator"], "Casey")
            self.assertIn("src/auth.py", d["files"])
            self.assertNotIn(".engine/records/gate-log.md", d["files"])
            self.assertTrue(d["records_transferred"])
            self.assertIn("src/auth.py", d["assessed"])
            self.assertTrue((t / "drop/records/gate-log.md").is_file())
            data, probs = topology.verify_drop(t / "drop")
            self.assertEqual(probs, [])

    def test_drop_only_from_the_low_side_and_names_the_operator(self):
        with tree() as t:
            low_side(t)
            with self.assertRaises(topology.TopologyError):
                topology.source_drop(t, t / "drop", cfg("high"), "Casey")
            with self.assertRaises(topology.TopologyError):
                topology.source_drop(t, t / "drop", cfg("low"), "  ")


class Receive(unittest.TestCase):
    def test_received_code_assessed_on_the_low_side_recorded_as_such(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
            high_side(hi)
            d = topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            self.assertTrue((hi / "src/auth.py").is_file())
            rows, _ = gatelog.series(hi)
            self.assertEqual([(r["unit"], r["side"]) for r in rows], [("U1", "low")])      # retained, distinguishable
            commit(hi, "receive drop")
            inv, counts = probes.write_inventory(hi, cfg("high"))
            states = {f: (s, e) for f, s, e in inv}
            self.assertEqual(states["src/auth.py"][0], "assessed")
            self.assertIn("U1#1 on side low (transferred with drop", states["src/auth.py"][1])
            ingest, _, _ = table.read(hi, topology.INGEST_RECORD, "ingest-records")
            self.assertEqual(len(ingest), 1)
            self.assertEqual((ingest[0]["hash_result"], ingest[0]["modified_in_transit"], ingest[0]["operator"], ingest[0]["side"]), ("verified", "no", "Dana", "high"))

    def test_received_without_records_is_the_third_state(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey", include_records=False)
            high_side(hi)
            topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            commit(hi, "receive drop")
            inv, counts = probes.write_inventory(hi, cfg("high"))
            self.assertEqual({f: s for f, s, _ in inv}["src/auth.py"], "assessed elsewhere, evidence not available")
            self.assertEqual(counts["elsewhere"], 3)

    def test_rows_claiming_this_side_are_refused_never_merged(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
            p = lo / "drop/records/gate-log.md"
            p.write_text(p.read_text(encoding="utf-8").replace("| low |", "| high |"), encoding="utf-8")
            m = lo / "drop/manifest.json"
            data = json.loads(m.read_text(encoding="utf-8"))
            data["records_sha256"]["gate-log.md"] = topology._sha256(p.read_bytes())
            m.write_text(json.dumps(data), encoding="utf-8")
            high_side(hi)
            with self.assertRaises(topology.TopologyError) as cm:
                topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            self.assertIn("never merged without a distinguishable side", str(cm.exception))

    def test_unenumerated_kind_refused_and_recorded(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
            m = lo / "drop/manifest.json"
            data = json.loads(m.read_text(encoding="utf-8"))
            data["kind"] = "records-sync"
            m.write_text(json.dumps(data), encoding="utf-8")
            high_side(hi)
            with self.assertRaises(topology.TopologyError) as cm:
                topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            self.assertIn("not enumerated to cross low->high", str(cm.exception))
            ingest, _, _ = table.read(hi, topology.INGEST_RECORD, "ingest-records")
            self.assertEqual(ingest[0]["hash_result"], "refused")
            # and the return path: a source drop from the high side is not something the low side receives
            data["kind"] = "source"; data["source_side"] = "high"
            m.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(topology.TopologyError) as cm:
                topology.receive_drop(lo, lo / "drop", cfg("low"), "Casey")
            self.assertIn("high->low", str(cm.exception))

    def test_filtered_drop_refused_unless_understood(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
            (lo / "drop/source.tar").write_bytes((lo / "drop/source.tar").read_bytes() + b"\0" * 512)
            high_side(hi)
            with self.assertRaises(topology.TopologyError) as cm:
                topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            self.assertIn("boundary filtered the content", str(cm.exception))
            self.assertIn("integrity incident", str(cm.exception))
            topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana", filtered_understood="gatekeeper pads archives to 512-byte blocks")
            ingest, _, _ = table.read(hi, topology.INGEST_RECORD, "ingest-records")
            self.assertEqual([r["modified_in_transit"][:3] for r in ingest], ["unk", "yes"])
            self.assertIn("gatekeeper pads archives", ingest[1]["modified_in_transit"])


class Divergence(unittest.TestCase):
    def received(self, lo, hi):
        low_side(lo)
        topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
        base = high_side(hi)
        topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
        recv = commit(hi, "receive drop")
        git(hi, "update-ref", "refs/remotes/origin/main", recv)
        return base, recv

    def test_received_content_is_not_a_high_side_change(self):
        with tree() as lo, tree() as hi:
            base, recv = self.received(lo, hi)
            self.assertEqual(topology.originated_here(hi, cfg("high"), base, recv), [])
            outs, ctx = gate.security_mechanical(hi, cfg("high"), base, recv, "H1")
            o = next(x for x in outs if x.check == "high-side-origin")
            self.assertIs(o.state, State.CLEAN)

    def test_high_side_edit_without_record_blocks_the_gate(self):
        with tree() as lo, tree() as hi:
            base, recv = self.received(lo, hi)
            git(hi, "checkout", "-q", "-b", "hotfix")
            write(hi, "src/auth.py", AUTH.replace("PermissionError", "PermissionError('no token')"))
            fix = commit(hi, "hotfix auth message")
            self.assertEqual(topology.originated_here(hi, cfg("high"), recv, fix), [fix])
            outs, ctx = gate.security_mechanical(hi, cfg("high"), recv, fix, "H2")
            o = next(x for x in outs if x.check == "high-side-origin")
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertIn(fix[:12], o.findings[0])
            self.assertIn("why it could not wait for the low-side path", o.findings[0])
            topology.record_change(hi, cfg("high"), commit=fix, what="auth error message", why_not_low_side="incident 44; transfer window is 9 days",
                                   authorized_by="Dana", backport_status="not yet ported")
            outs, ctx = gate.security_mechanical(hi, cfg("high"), recv, fix, "H2")
            self.assertIs(next(x for x in outs if x.check == "high-side-origin").state, State.CLEAN)

    def test_record_fields_and_backport_statuses(self):
        with tree() as lo, tree() as hi:
            base, recv = self.received(lo, hi)
            c = cfg("high")
            for bad in ("", "ported", "will not be ported", "will not be ported: no", "maybe later"):
                self.assertIsNotNone(topology.backport_problem(bad), bad)
            for ok in ("not yet ported", "ported at revision 1a2b3c4d", "will not be ported: the high-side build uses a different TLS stack"):
                self.assertIsNone(topology.backport_problem(ok), ok)
            with self.assertRaises(topology.TopologyError):
                topology.record_change(hi, c, commit=recv, what="x", why_not_low_side="", authorized_by="Dana", backport_status="not yet ported")
            with self.assertRaises(topology.TopologyError):
                topology.record_change(hi, cfg("low"), commit=recv, what="x", why_not_low_side="y", authorized_by="Dana", backport_status="not yet ported")
            with self.assertRaises(topology.TopologyError):
                topology.record_change(hi, c, commit=recv, what="x", why_not_low_side="y", authorized_by="Dana", backport_status="will not be ported")
            topology.record_change(hi, c, commit=recv, what="x", why_not_low_side="y", authorized_by="Dana", backport_status="not yet ported")
            self.assertEqual(len(topology.unported(hi)), 1)
            topology.record_change(hi, c, commit=recv, what="x", why_not_low_side="y", authorized_by="Dana", backport_status="ported at revision abc1234")
            self.assertEqual(topology.unported(hi), [])
            rows, _ = topology.changes(hi)
            self.assertEqual(rows[0]["backport_status"], "ported at revision abc1234")

    def test_unported_count_at_every_gate_and_ungated_change_blocks(self):
        with tree() as lo, tree() as hi:
            base, recv = self.received(lo, hi)
            c = cfg("high")
            self.assertIs(high_side_changes.run(hi, c).state, State.NOTHING_YET)
            git(hi, "checkout", "-q", "-b", "hotfix")
            write(hi, "src/auth.py", AUTH + "# tightened" + NL)
            fix = commit(hi, "hotfix")
            topology.record_change(hi, c, commit=fix, what="tightened", why_not_low_side="incident", authorized_by="Dana", backport_status="not yet ported")
            o = high_side_changes.run(hi, c)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertIn("no high-side gate row covers it", o.findings[0])
            self.assertIn("high-side changes unported: 1", o.detail)
            gatelog.append(hi, c, unit="H2", range=f"{recv[:12]}..{fix[:12]}", run="1", verdict="pass", reviewer="security-gate",
                           reviewer_class="automated-with-human-review", model="m 7B", attested_by="Dana", harness_version="0.1.0", checklist_version="cl-abc")
            o = high_side_changes.run(hi, c)
            self.assertIs(o.state, State.CLEAN)
            outs, ctx = gate.security_mechanical(hi, c, recv, fix, "H3")
            self.assertIn("high-side changes unported: 1 (" + fix[:12] + ")", next(x for x in outs if x.check == "high-side-changes").line())
            self.assertIs(high_side_changes.run(hi, cfg("high", topology="single")).state, State.NOT_APPLICABLE)


class Export(unittest.TestCase):
    def test_high_side_export_is_self_contained_and_carries_ingest_and_divergence(self):
        with tree() as lo, tree() as hi:
            low_side(lo)
            topology.source_drop(lo, lo / "drop", cfg("low"), "Casey")
            high_side(hi)
            topology.receive_drop(hi, lo / "drop", cfg("high"), "Dana")
            recv = commit(hi, "receive drop")
            c = cfg("high")
            topology.record_change(hi, c, commit=recv, what="x", why_not_low_side="y", authorized_by="Dana", backport_status="not yet ported")
            write(hi, ".engine/control-manifest.json", json.dumps({"schema": 1, "scope_statement": __import__("engine.manifest", fromlist=["x"]).SCOPE_STATEMENT, "controls": []}))
            out, m = export.package(hi, c, hi / "exports")
            paths = {e["path"] for e in m["files"]}
            for must in ("records/ingest-records.md", "records/high-side-changes.md", "records/received-drops.json", "04-record-authority.md", "records/coverage-inventory.md"):
                self.assertIn(must, paths, must)
            disc = (out / "00-DISCLOSURE.md").read_text(encoding="utf-8")
            line_with(disc, "side: high; topology: high-side")
            line_with(disc, "- high-side changes unported: 1")
            line_with(disc, "this record set is the deliverable one for anything assessed against the high-side system")
            inv = (out / "records/coverage-inventory.md").read_text(encoding="utf-8")
            line_with(inv, "- assessed elsewhere, evidence not available: 0 (0%)")
            self.assertEqual(m["side"], "high")
