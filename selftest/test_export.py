# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Evidence export (spec 02 §10, §6.4; spec 04 §6–7; spec 01 REQ-4.9.2, REQ-1.5.2)."""
import datetime
import json
import unittest

from engine import export, manifest
from engine.records import gatelog, table
from engine.records import schema as sch
from .helpers import cli, commit, find_line, tree, write, line_with
from .test_gate import APP, AUTH, TEST, cfg, feature, project as gate_project

NL = chr(10)
DIGEST = "sha256:" + "ab" * 32
RAW = ('{"matches":[{"vulnerability":{"id":"CVE-2024-3094","severity":"Critical"},"artifact":{"name":"xz-utils","version":"5.6.0"}}],'
       '"source":{"target":{"userInput":"123456789012.dkr.ecr.us-gov-west-1.amazonaws.com/team/app:1.4","imageID":"' + DIGEST + '",'
       '"host":"build-07.corp.example.mil"}},"descriptor":{"configuration":{"file":"/home/casey/.grype.yaml"}}}')


def project(t, **over):
    """The gate fixture with one real declared control, a mutation result, a gate row
    naming the control, a carried finding against it, raw scan output and an SBOM."""
    base = gate_project(t, **over)
    head = feature(t)
    write(t, manifest.FILE, json.dumps({"schema": 1, "scope_statement": manifest.SCOPE_STATEMENT, "controls": [
        {"id": "AC-3.1", "description": "Every item route requires a bearer token.", "location": {"file": "src/auth.py", "symbol": "require_auth"},
         "required_artifact": None, "test_pattern": "tests/test_items*", "status": "hybrid", "counterpart": "platform IAM (inherited)", "mutation": None}]}))
    c = cfg()
    table.append(t, ".engine/records/mutation-results.md", sch.MUTATION, {
        "date": "2026-09-01", "control": "AC-3.1", "branch": "mutate/AC-3.1", "mutation": "decision inverted", "baseline": "pass", "result": "detected", "side": "low"})
    gatelog.append(t, c, unit="U1", range=f"{base[:12]}..{head[:12]}", run="1", verdict="pass", reviewer="security-gate",
                   reviewer_class="automated-with-human-review", model="reviewer-x 70B", attested_by="Casey", controls="AC-3.1",
                   harness_version="0.1.0", checklist_version="cl-abc")
    table.append(t, ".engine/records/carried-findings.md", sch.CARRIED, {
        "id": "CF-9", "component": "xz-utils", "version": "5.6.0", "severity": "critical", "reason_no_fix": "no upstream fix; affects AC-3.1 path",
        "owner": "Casey", "milestone": "M2", "milestone_date": "2026-12-01", "review_by": "2026-10-15", "status": "open", "status_history": "2026-09-01 opened", "side": "low"})
    write(t, ".engine/scan/raw/grype-app.json", RAW)
    write(t, ".engine/scan/sbom/app.cdx.json", '{"bomFormat":"CycloneDX","components":[{"name":"xz-utils","version":"5.6.0"}]}')
    write(t, ".engine/scan/actionable.md", "# Actionable" + NL + "- CVE-2024-3094 xz-utils 5.6.0 (image " + DIGEST + ")" + NL)
    write(t, ".engine/detection-data-date", "2026-09-10")
    return base, head, commit(t, "records")


class Traceability(unittest.TestCase):
    def test_joins_every_source_per_control_in_srtm_shape(self):
        with tree() as t:
            project(t)
            idx = export.traceability(t, cfg())
            self.assertEqual(idx["scope_statement"], manifest.SCOPE_STATEMENT)
            self.assertEqual(len(idx["rows"]), 1)
            r = idx["rows"][0]
            self.assertEqual(r["Control ID"], "AC-3.1")
            self.assertEqual(r["Implementation Status"], "hybrid")
            self.assertIn("platform IAM (inherited)", r["Responsible Party"])
            self.assertTrue(r["Implementation"].startswith("src/auth.py:require_auth (line"))
            self.assertIn("tests/test_items.py", r["Test Evidence"])
            self.assertIn("detected (2026-09-01; baseline pass; decision inverted)", r["Developer Testing"])
            self.assertIn("U1#1 pass", r["Assessment Records"])
            self.assertEqual(r["Open Findings"], "CF-9")
            text = export.render_traceability(idx, "abc123")
            line_with(text, "| " + " | ".join(export.SRTM_COLUMNS) + " |")
            line_with(text, manifest.SCOPE_STATEMENT)
            line_with(text, "commit: abc123")

    def test_missing_evidence_is_named_not_blank(self):
        with tree() as t:
            project(t)
            write(t, ".engine/records/mutation-results.md", (t / ".engine/records/mutation-results.md").read_text(encoding="utf-8").replace("| detected |", "| detected |").split("| 2026-09-01")[0])
            from engine.records import templates
            write(t, ".engine/records/mutation-results.md", templates.mutation_results())
            r = export.traceability(t, cfg())["rows"][0]
            self.assertIn("no mutation result recorded", r["Developer Testing"])
            self.assertIn("not been proven by breaking it", r["Developer Testing"])

    def test_superseded_gate_rows_do_not_count_as_assessment(self):
        with tree() as t:
            base, head, _ = project(t)
            gatelog.supersede(t, cfg(), "U1", "1", "checklist misapplied", "audit", "re-run", "Casey", "Casey")
            r = export.traceability(t, cfg())["rows"][0]
            self.assertIn("no gate run records assessing this control", r["Assessment Records"])

    def test_invalid_manifest_refuses_the_index(self):
        with tree() as t:
            project(t)
            d = json.loads((t / manifest.FILE).read_text(encoding="utf-8"))
            d["controls"][0]["counterpart"] = None
            write(t, manifest.FILE, json.dumps(d))
            with self.assertRaises(export.ExportError) as cm:
                export.traceability(t, cfg())
            self.assertIn("counterpart", str(cm.exception))

    def test_narrative_is_prose_from_manifest_and_code(self):
        with tree() as t:
            project(t)
            idx = export.traceability(t, cfg())
            text = export.narrative(t, idx)
            line_with(text, "## AC-3.1")
            body = line_with(text, "implemented by `require_auth` in `src/auth.py`")
            self.assertIn("hybrid control", body)
            line_with(text, "Every item route requires a bearer token.")


class Disclosure(unittest.TestCase):
    def test_generated_from_records_and_distinguishes_artifact_classes(self):
        with tree() as t:
            project(t)
            text = export.disclosure(t, cfg(), "abc123")
            self.assertTrue(text.startswith("# Disclosure statement"))
            line_with(text, "automated reviewers applying a versioned checklist")
            line_with(text, "- checklist versions applied: cl-abc")
            line_with(text, "- models named: reviewer-x 70B")
            line_with(text, "- attested by: Casey")
            line_with(text, "- reviewer classes seen: automated-with-human-review")
            d = text.index("## Deterministic artifacts")
            n = text.index("## Non-deterministic artifacts")
            h = text.index("## Human-authored artifacts")
            self.assertLess(d, n)
            self.assertLess(n, h)
            self.assertIn("mutation results", text[d:n])
            self.assertIn("mechanical check registry: config,", text[d:n])
            self.assertIn("agent reviewer", text[n:h])
            line_with(text, "reconciliation obligations open: 0")

    def test_disclosure_reflects_record_changes_not_a_hand_maintained_text(self):
        with tree() as t:
            base, head, _ = project(t)
            before = export.disclosure(t, cfg(), "abc")
            gatelog.append(t, cfg(), unit="U2", range=f"{base[:12]}..{head[:12]}", run="1", verdict="pass", reviewer="r",
                           reviewer_class="human", model="-", attested_by="Dana", harness_version="0.1.0", checklist_version="cl-def")
            after = export.disclosure(t, cfg(), "abc")
            self.assertNotEqual(before, after)
            self.assertIn("attested by: Casey, Dana", after)
            self.assertIn("cl-abc, cl-def", after)
            self.assertIn("Gate rows in this package: 2 live", after)


class Redaction(unittest.TestCase):
    def test_environment_identifiers_out_vulnerability_content_stays(self):
        out = export.redact(RAW)
        for gone in (DIGEST, "123456789012", "build-07.corp.example.mil", "dkr.ecr", "casey"):
            self.assertNotIn(gone, out)
        for stays in ("CVE-2024-3094", "xz-utils", "5.6.0", "Critical"):
            line_with(out, stays)
        self.assertEqual(export.redaction_problems(out), [])
        self.assertTrue(export.redaction_problems(RAW))

    def test_scan_bundle_is_dated_redacted_and_hashed(self):
        with tree() as t:
            project(t)
            meta = export.scan_bundle(t, t / "out", cfg())
            self.assertEqual(meta["kind"], "scan-bundle")
            self.assertTrue(meta["date"].startswith("20"))
            self.assertTrue(meta["redacted"])
            self.assertEqual(meta["detection_data_date"], "2026-09-10")
            paths = {f["path"] for f in meta["files"]}
            self.assertIn("raw/grype-app.json", paths)
            self.assertIn("sbom/app.cdx.json", paths)
            self.assertIn("actionable.md", paths)
            text = (t / "out/raw/grype-app.json").read_text(encoding="utf-8")
            self.assertNotIn(DIGEST, text)
            line_with(text, "CVE-2024-3094")
            line_with((t / "out/actionable.md").read_text(encoding="utf-8"), "<redacted digest>")
            raw = export.scan_bundle(t, t / "raw", cfg(), redacted=False)
            self.assertFalse(raw["redacted"])
            self.assertIn(DIGEST, (t / "raw/raw/grype-app.json").read_text(encoding="utf-8"))

    def test_bundle_refuses_when_its_own_redaction_leaves_an_identifier(self):
        with tree() as t:
            project(t)
            original = export.redact
            export.redact = lambda text: text
            try:
                with self.assertRaises(export.ExportError) as cm:
                    export.scan_bundle(t, t / "out", cfg())
            finally:
                export.redact = original
            self.assertIn("redaction incomplete", str(cm.exception))


class Package(unittest.TestCase):
    def test_bundle_is_dated_bound_to_commit_hashed_and_complete(self):
        with tree() as t:
            base, head, rec = project(t)
            out, m = export.package(t, cfg(retention={"authorization_period_years": 3, "audit_retention_years": 3}), t / "exports")
            self.assertEqual(out.name, f"evidence-{datetime.date.today().isoformat()}-{rec[:12]}")
            self.assertEqual(m["commit"], rec)
            self.assertEqual(m["incomplete"], [])
            paths = {e["path"] for e in m["files"]}
            for must in ("00-DISCLOSURE.md", "01-traceability-index.md", "02-implementation-narrative.md", "03-degradation-statement.md",
                         "gate-log/gate-log.md", "records/findings-register.md", "records/governance-changelog.md", "records/standing-state-deltas.md",
                         "records/coverage-inventory.md", "records/plan-of-action.md", "records/reconciliation-obligations.md",
                         "sbom/app.cdx.json", "scan/raw/grype-app.json", "scan/BUNDLE.json", "RETENTION.md", "index.html"):
                self.assertIn(must, paths, must)
            self.assertEqual(sorted(paths)[0], "00-DISCLOSURE.md")     # the disclosure is at the front
            ok, probs = export.verify(out)
            self.assertTrue(ok, probs)
            self.assertNotIn(DIGEST, (out / "scan/raw/grype-app.json").read_text(encoding="utf-8"))
            self.assertIn("## not achieved", (out / "03-degradation-statement.md").read_text(encoding="utf-8"))
            self.assertIn("retain at least 6 years", (out / "RETENTION.md").read_text(encoding="utf-8"))
            self.assertIn("xz-utils", (out / "sbom/app.cdx.json").read_text(encoding="utf-8"))
            with self.assertRaises(export.ExportError):
                export.package(t, cfg(), t / "exports")        # never overwritten

    def test_hashes_computed_at_export_and_tampering_detected(self):
        with tree() as t:
            project(t)
            out, m = export.package(t, cfg(), t / "exports")
            p = out / "01-traceability-index.md"
            p.write_text(p.read_text(encoding="utf-8") + "edited" + NL, encoding="utf-8")
            (out / "extra.txt").write_text("x", encoding="utf-8")
            ok, probs = export.verify(out)
            self.assertFalse(ok)
            self.assertTrue(any("01-traceability-index.md: content differs" in x for x in probs))
            self.assertTrue(any("extra.txt: present but not in the manifest" in x for x in probs))

    def test_marking_uniform_or_refused(self):
        with tree() as t:
            project(t)
            with self.assertRaises(export.ExportError) as cm:
                export.package(t, cfg(marking_required=True), t / "exports")
            self.assertIn("marking is required", str(cm.exception))
            self.assertFalse((t / "exports").exists() and any((t / "exports").iterdir()))
            out, m = export.package(t, cfg(marking_required=True, classification_marking="CUI // SP-CTI"), t / "exports")
            self.assertEqual(m["marking"], "CUI // SP-CTI")
            for e in m["files"] + [{"path": "MANIFEST.json"}]:
                text = (out / e["path"]).read_text(encoding="utf-8")
                if e["path"].endswith(".json"):
                    self.assertEqual(json.loads(text)["_classification_marking"], "CUI // SP-CTI", e["path"])
                elif e["path"].endswith(".html"):
                    self.assertEqual(text.count('<p class="marking">CUI // SP-CTI</p>'), 2, e["path"])
                else:
                    self.assertTrue(text.startswith("CUI // SP-CTI"), e["path"])
                    self.assertIn("CUI // SP-CTI", text[-40:], e["path"])

    def test_incomplete_package_says_what_is_missing(self):
        with tree() as t:
            project(t)
            import shutil
            shutil.rmtree(t / ".engine/scan/sbom")
            out, m = export.package(t, cfg(), t / "exports")
            self.assertTrue(any("no composition inventory" in x for x in m["incomplete"]))
            self.assertTrue(any("retention period not configured" in x for x in m["incomplete"]))
            self.assertIn("NOT CONFIGURED", (out / "RETENTION.md").read_text(encoding="utf-8"))
            self.assertIn("plain text in version control", (out / "RETENTION.md").read_text(encoding="utf-8"))

    def test_open_obligations_counted_in_every_export(self):
        with tree() as t:
            from engine import field
            base, head, _ = project(t)
            field.declare(t, cfg(), by="Casey", reason="edge", impossible="no reachback", budget_seconds=0)
            from .test_field import fake_clock
            field.run(t, cfg(), "F1", 1, base, head, "Casey", clock=fake_clock([0, 5]))
            text = export.disclosure(t, cfg(), "abc")
            line_with(text, "reconciliation obligations open: 1 (OB-F1-1)")
            line_with(text, "Field-mode rows: 1")


class Retention(unittest.TestCase):
    def test_period_is_authorization_plus_audit_and_outlives_the_harness(self):
        today = datetime.date(2026, 9, 20)
        r = export.retention(cfg(retention={"authorization_period_years": 3, "audit_retention_years": 3}), today)
        self.assertTrue(r["configured"])
        self.assertEqual(r["years"], 6)
        self.assertEqual(r["retain_until"], "2032-09-20")
        self.assertIn("until 2032-09-20", r["statement"])
        self.assertIn("plain text in version control", r["statement"])
        self.assertIn("does not depend on the harness", r["statement"])
        u = export.retention(cfg(), today)
        self.assertFalse(u["configured"])
        self.assertIn("plain text in version control", u["statement"])


class Offline(unittest.TestCase):
    def test_index_renders_with_nothing_fetched(self):
        html = export.render_index([{"path": "00-DISCLOSURE.md", "kind": "d", "sha256": "0" * 64}], "abc123", None)
        self.assertEqual(export.offline_problems(html), [])
        self.assertIn("system-ui", html)
        self.assertIn("<svg", html)
        self.assertNotIn("http", html)
        self.assertNotIn("<script", html)

    def test_offline_guard_names_each_violation(self):
        base = export.render_index([], "abc", None)
        self.assertTrue(any("fetches" in p for p in export.offline_problems(base.replace("<table>", '<link rel="stylesheet" href="https://cdn.example.com/x.css"><table>'))))
        self.assertTrue(any("script" in p for p in export.offline_problems(base.replace("<table>", '<script src="x.js"></script><table>'))))
        self.assertTrue(any("typeface" in p for p in export.offline_problems(base.replace("system-ui,", ""))))
        self.assertTrue(any("image" in p for p in export.offline_problems(base.replace("<table>", '<img src="diagram.png"><table>'))))

    def test_package_refuses_a_page_that_would_not_render_offline(self):
        with tree() as t:
            project(t)
            original = export.DIAGRAM
            export.DIAGRAM = '<img src="https://cdn.example.com/diagram.png">'
            try:
                with self.assertRaises(export.ExportError) as cm:
                    export.package(t, cfg(), t / "exports")
            finally:
                export.DIAGRAM = original
            self.assertIn("would not render offline", str(cm.exception))


class Cli(unittest.TestCase):
    def test_package_and_verify_round_trip(self):
        with tree() as t:
            project(t)
            code, out = cli(t, "export", "package", f"out={t / 'x'}")
            self.assertEqual(code, 1, out)     # retention not configured: incomplete, and says so
            find_line(out, "  INCOMPLETE: retention period not configured")
            pkg = [l for l in out if l.startswith("export: ") and "evidence-" in l][0].split("export: ", 1)[1]
            code, out = cli(t, "export", "verify", pkg)
            self.assertEqual(code, 0, out)
            find_line(out, "export: VERIFIED")
            code, out = cli(t, "export", "traceability")
            self.assertEqual(code, 0)
            self.assertTrue(any(l.startswith("| AC-3.1 |") for l in out))
