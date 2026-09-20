# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Standards citation and currency (spec 01 §8; spec 04 §3; spec 06 REQ-8.5)."""
import json
import shutil
import unittest

from engine import catalogue, distribute
from engine.checks import citations
from engine.config import Config
from engine.outcome import State
from .helpers import ROOT, cli, find_line, tree, write, write_config, line_with

NL = chr(10)


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local",
         "governed_documents": ["docs/*.md"]}
    d.update(over)
    return Config(d)


def seeded(t):
    write_config(t, governed_documents=["docs/*.md"])
    distribute.update(t)      # places the seed catalogues with provenance
    return t


def cats(t):
    return catalogue.load_all(t)


class Catalogue(unittest.TestCase):
    def test_seed_catalogues_load_with_provenance_and_no_text(self):
        with tree() as t:
            seeded(t)
            c = cats(t)
            self.assertIn("nist-sp-800-53-r5", c)
            prov = c["nist-sp-800-53-r5"]["_provenance"]
            for k in ("source", "source_sha256", "version", "retrieved", "sha256", "redistribution"):
                self.assertIn(k, prov)
            for ident, e in c["nist-sp-800-53-r5"]["entries"].items():
                self.assertNotIn("text", e, f"{ident} must not carry control text")
                self.assertIn(e["status"], ("active", "withdrawn"))
                if e["status"] == "withdrawn":
                    self.assertTrue(e["superseded_by"], ident)

    def test_hash_mismatch_refused(self):
        with tree() as t:
            seeded(t)
            p = t / catalogue.DIR / "publications.json"
            p.write_text(p.read_text(encoding="utf-8").replace("Rev 2", "Rev 9"), encoding="utf-8")
            with self.assertRaises(catalogue.CatalogueError) as cm:
                cats(t)
            self.assertIn("content hash differs from its provenance", str(cm.exception))

    def test_structure_rules(self):
        self.assertIn("X-1: catalogues do not store control text", catalogue.problems(
            {"key": "k", "publication": "p", "revision": "r", "entries": {"X-1": {"status": "active", "title": "t", "text": "..."}}}))
        self.assertIn("X-1: withdrawn without naming what superseded it", catalogue.problems(
            {"key": "k", "publication": "p", "revision": "r", "entries": {"X-1": {"status": "withdrawn", "title": "t"}}}))

    def test_ingest_is_explicit_and_produces_a_diff(self):
        with tree() as t:
            seeded(t)
            newer = json.loads((t / catalogue.DIR / "publications.json").read_text(encoding="utf-8"))
            newer["entries"]["NIST SP 800-52"]["current_revision"] = "Rev 3"
            newer["entries"]["NIST SP 800-52"]["published_revisions"].append("Rev 3")
            newer["entries"]["NIST SP 800-999"] = {"status": "active", "title": "New"}
            write(t, "incoming.json", json.dumps(newer))
            d = catalogue.ingest(t, t / "incoming.json")
            self.assertIn("+ NIST SP 800-999: active — New", d)
            self.assertTrue(any(l.startswith("~ NIST SP 800-52:") for l in d), d)
            self.assertEqual(cats(t)["publications"]["entries"]["NIST SP 800-52"]["current_revision"], "Rev 3")
            self.assertEqual(cats(t)["publications"]["_provenance"]["source"], "operator-supplied: incoming.json")

    def test_ingest_refuses_handling_markings_unless_acknowledged(self):
        with tree() as t:
            seeded(t)
            doc = json.loads((t / catalogue.DIR / "publications.json").read_text(encoding="utf-8"))
            write(t, "marked.json", "CUI//SP-CTI" + NL + json.dumps(doc))
            with self.assertRaises(catalogue.CatalogueError) as cm:
                catalogue.ingest(t, t / "marked.json")
            self.assertIn("handling marking (CUI)", str(cm.exception))
            with self.assertRaises(catalogue.CatalogueError):
                catalogue.ingest(t, t / "marked.json", acknowledge_markings=True)   # not valid JSON with the banner; refusal is about markings first
            write(t, "marked2.json", json.dumps(doc))
            self.assertIsInstance(catalogue.ingest(t, t / "marked2.json", acknowledge_markings=True), list)

    def test_oscal_conversion(self):
        oscal = {"catalog": {"metadata": {"version": "5.1.1"}, "groups": [{"controls": [
            {"id": "ac-1", "title": "Policy and Procedures", "props": []},
            {"id": "sa-12", "title": "Supply Chain Protection", "props": [{"name": "status", "value": "withdrawn"}],
             "links": [{"rel": "incorporated-into", "href": "#sr-2"}]}]}]}}
        cat = catalogue.from_oscal(json.dumps(oscal))
        self.assertEqual(cat["revision"], "Rev 5")
        self.assertEqual(cat["entries"]["AC-1"], {"status": "active", "title": "Policy and Procedures"})
        self.assertEqual(cat["entries"]["SA-12"]["superseded_by"], ["SR-2"])

    def test_transfer_bundle_verifies_hash_and_diffs(self):
        with tree() as src, tree() as dst:
            seeded(src); seeded(dst)
            newer = json.loads((src / catalogue.DIR / "publications.json").read_text(encoding="utf-8"))
            newer["entries"]["NIST SP 800-777"] = {"status": "active", "title": "Newer"}
            write(src, "n.json", json.dumps(newer)); catalogue.ingest(src, src / "n.json")
            m = catalogue.bundle(src, src / "out")
            self.assertEqual(m["kind"], "catalogues")
            diffs = catalogue.ingest_bundle(dst, src / "out")
            self.assertEqual(set(diffs), set(cats(src)))
            self.assertEqual(diffs["publications"], ["+ NIST SP 800-777: active — Newer"], "ingestion produces a reviewable diff")
            (src / "out" / "catalogues.tar").write_bytes(b"tampered")
            with self.assertRaises(catalogue.CatalogueError):
                catalogue.ingest_bundle(dst, src / "out")

    def test_data_statement_names_every_vendored_set(self):
        text = (ROOT / "engine/data/README.md").read_text(encoding="utf-8")
        for name in ("nist-sp-800-53-r5.json", "publications.json", "owasp-top10.json", "OWASP MASVS", "Model weights"):
            line_with(text, name)
        line_with(text, "public domain")
        self.assertTrue(any("OWASP MASVS | Not vendored" in l for l in text.splitlines()), "operator-supplied sets are stated as such")


class Verification(unittest.TestCase):
    def check(self, t, text):
        write(t, "docs/policy.md", text)
        return citations.run(t, cfg())

    def test_active_identifiers_resolve(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "We enforce AC-2 and SC-7; see NIST SP 800-53 Rev 5 and FIPS 140-3." + NL)
            self.assertIs(o.state, State.CLEAN, o.lines())

    def test_withdrawn_identifier_fails_naming_replacement(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Grounded in SA-12." + NL)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: SA-12 is withdrawn — replaced by SR-2, SR-3, SR-5, SR-6, SR-8, SR-9, SR-10, SR-11"])

    def test_deliberate_historical_mention_allowed(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Formerly SA-12 (withdrawn), now SR-3." + NL)
            self.assertIs(o.state, State.CLEAN, o.lines())

    def test_never_published_revision_fails_and_superseded_revision_reports(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Per NIST SP 800-53 Rev 7." + NL)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: NIST SP 800-53 Rev 7 was never published — published: Rev 4, Rev 5"])
            o = self.check(t, "Per NIST SP 800-53 Rev 4." + NL)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: NIST SP 800-53 Rev 4 is superseded — current revision is Rev 5"])

    def test_stale_edition_numbering_fails_naming_current_title(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Covers OWASP Top 10 A1:2017 injection." + NL)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: OWASP Top 10 A1:2017 uses stale edition numbering — A01 now carries the title 'Broken Access Control' (2021)"])

    def test_platform_not_indexed_reports_with_path(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Mobile storage per OWASP MASVS-STORAGE." + NL)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertIn("supply its catalogue with `catalogue ingest`", o.findings[0])

    def test_declared_unindexed_platform_is_a_recorded_acceptance(self):
        with tree() as t:
            seeded(t)
            write(t, "docs/policy.md", "Mobile storage per OWASP MASVS-STORAGE and AC-2." + NL)
            o = citations.run(t, cfg(citation_platforms_unindexed=["MASVS"]))
            self.assertIs(o.state, State.CLEAN, o.lines())
            self.assertIn("1 citation(s) on platform(s) the project declares unindexed (MASVS) — a recorded acceptance", o.detail)

    def test_withdrawn_publication_fails(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Modules validated to FIPS 140-2." + NL)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: FIPS 140-2 is withdrawn — replaced by FIPS 140-3"])

    def test_prose_resembling_identifiers_not_misread(self):
        with tree() as t:
            seeded(t)
            o = self.check(t, "Ticket ABC-12 and DEF-99 closed; version 3.1-2; MAC-2 address; see A1 paper." + NL)
            self.assertIs(o.state, State.NOTHING_YET, o.lines())

    def test_unknown_identifier_in_full_catalogue_fails(self):
        with tree() as t:
            seeded(t)
            full = json.loads((t / catalogue.DIR / "nist-sp-800-53-r5.json").read_text(encoding="utf-8"))
            full["coverage"] = "full"
            write(t, "full.json", json.dumps(full))
            catalogue.ingest(t, t / "full.json")
            o = self.check(t, "We cite AC-99." + NL)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["docs/policy.md: line 1: AC-99 is unknown — typo, invented, or from another framework"])

    def test_governed_set_is_explicit(self):
        with tree() as t:
            seeded(t)
            write(t, "notes/x.md", "SA-12 everywhere" + NL)
            write(t, "docs/policy.md", "AC-2" + NL)
            self.assertIs(citations.run(t, cfg()).state, State.CLEAN)

    def test_no_catalogues_is_could_not_run(self):
        with tree() as t:
            write_config(t, governed_documents=["docs/*.md"])
            write(t, "docs/policy.md", "AC-2" + NL)
            self.assertIs(citations.run(t, cfg()).state, State.COULD_NOT_RUN)

    def test_harness_own_checklist_citations_resolve(self):
        with tree() as t:
            shutil.copytree(ROOT / "engine" / "data" / "catalogues", t / ".engine" / "catalogues")
            shutil.copytree(ROOT / "engine" / "dist" / "agents", t / "agents")
            o = citations.run(t, Config({"governed_documents": ["agents/*.md"]}))
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking, "only MASVS (platform not indexed) may be reported; nothing may fail")
            self.assertTrue(all("MASVS" in f for f in o.findings), o.findings)


class Currency(unittest.TestCase):
    def test_offline_reports_not_checked_and_exits_zero(self):
        with tree() as t:
            seeded(t)
            lines, code = catalogue.currency(t, cfg(mode="disconnected"), offline=True)
            self.assertEqual(code, 0)
            self.assertTrue(lines[0].startswith("currency: NOT CHECKED"), lines)
            self.assertIn("currency: last successful verification: never", lines)

    def test_disconnected_fetch_without_flag_is_an_error(self):
        with tree() as t:
            seeded(t)
            lines, code = catalogue.currency(t, cfg(mode="disconnected"))
            self.assertEqual(code, 1)
            self.assertTrue(lines[0].startswith("currency: ERROR — mode is disconnected"))

    def test_connected_compares_pins_and_records_verification_date(self):
        with tree() as t:
            seeded(t)
            fetched = []
            def fetch(url):
                fetched.append(url)
                return b"published catalogue bytes"
            lines, code = catalogue.currency(t, cfg(mode="connected"), fetch=fetch)
            self.assertEqual(code, 3, lines)
            self.assertTrue(any("differs from the pinned source" in l and "nothing is adopted automatically" in l for l in lines), lines)
            self.assertTrue((t / catalogue.CURRENCY_FILE).is_file())
            self.assertTrue(any("0 day(s) ago" in l for l in lines))
            self.assertEqual(len(fetched), 1, "only catalogues with an indexed source are fetched")
            self.assertEqual(cats(t)["nist-sp-800-53-r5"]["_provenance"]["source_sha256"], "seed-transcription",
                             "a differing published catalogue is reported, never adopted automatically")

    def test_only_the_currency_command_reaches_the_network(self):
        import re
        for p in (ROOT / "engine").rglob("*.py"):
            if p.name in ("net.py", "catalogue.py"):
                continue
            self.assertNotIn("net.fetch(", p.read_text(encoding="utf-8"), p.name)
        src = (ROOT / "engine/catalogue.py").read_text(encoding="utf-8")
        self.assertIn('caller="currency"', src)


class Cli(unittest.TestCase):
    def test_commands(self):
        with tree() as t:
            seeded(t)
            code, lines = cli(t, "currency", "--offline")
            self.assertEqual(code, 0)
            find_line(lines, "currency: NOT CHECKED")
            code, lines = cli(t, "catalogue", "bundle", str(t / "out"))
            self.assertEqual(code, 0, lines)
            code, lines = cli(t, "catalogue", "ingest-bundle", str(t / "out"))
            self.assertEqual(code, 0, lines)
