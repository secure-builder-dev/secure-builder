# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Enforcement points for the non-negotiables (spec 03 REQ-1.2.3); constructed fixtures
and audit dispositions (spec 05 REQ-2.4, REQ-10.2); no registry credentials and no
registry access for the scanner (spec 04 REQ-4.3.1–4.3.2); no exemption from
engine-owned overwrite (spec 06 REQ-2.1.3)."""
import json
import shutil
import unittest

from engine import audit, distribute, enforcement
from engine import ownership as own
from engine.checks import credential_scan
from engine.outcome import State
from engine.records import findings, templates
from .helpers import ROOT, cli, tree, write, write_config

NL = chr(10)
RULES = "engine/dist/rules/RULES.md"


def harness_copy(t):
    """A copy of the harness source tree, so its rulebook and hooks can be altered."""
    shutil.copytree(ROOT / "engine", t / "engine", ignore=shutil.ignore_patterns("__pycache__"))
    (t / "selftest").mkdir()
    write(t, "selftest/__init__.py", "")


class Enforcement(unittest.TestCase):
    def test_real_rulebook_has_a_verifiable_point_per_rule(self):
        o = enforcement.run(ROOT, None)
        self.assertIs(o.state, State.CLEAN, o.lines())
        self.assertIn("7 non-negotiables", o.detail)
        self.assertEqual(enforcement.rules_in_text(ROOT), [1, 2, 3, 4, 5, 6, 7])

    def test_rule_added_as_prose_only_is_blocking(self):
        with tree() as t:
            harness_copy(t)
            p = t / RULES
            text = p.read_text(encoding="utf-8")
            text = text.replace("## Precedence", "8. You never run the tests with network access." + NL + NL + "## Precedence")
            p.write_text(text, encoding="utf-8")
            o = enforcement.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertIn("rule 8 exists only as prose", o.findings[0])

    def test_recorded_point_that_does_not_exist_is_blocking(self):
        with tree() as t:
            harness_copy(t)
            (t / "engine/checks/negative_fixtures.py").unlink()
            o = enforcement.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(any("rule 6: the recorded mechanical-check enforcement point" in f for f in o.findings))

    def test_platform_only_rule_is_reported_not_counted(self):
        with tree() as t:
            harness_copy(t)
            import unittest.mock as mock
            pts = dict(enforcement.POINTS)
            pts[6] = [("platform", "the platform enforces it", "platform:x")]
            with mock.patch.object(enforcement, "POINTS", pts):
                o = enforcement.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(any("rule 6: every recorded enforcement point is a platform assertion" in f for f in o.findings))

    def test_no_rulebook_is_could_not_run(self):
        with tree() as t:
            write(t, "x", "")
            self.assertIs(enforcement.run(t, None).state, State.COULD_NOT_RUN)


class Fixtures(unittest.TestCase):
    def test_borrowed_fixtures_reported_constructed_ones_not(self):
        with tree() as t:
            outside = "op" + "en('.." + "/prod/export.json')"     # assembled so this file does not itself trip Q9
            write(t, "tests/test_a.py", "def test_x():" + NL + "    data = " + outside + ".read()" + NL)
            write(t, "tests/fixtures/prod-export-2026.json", "{}")
            write(t, "tests/fixtures/small-constructed.json", '{"k": 1}')
            (t / "tests/fixtures/big.bin").write_bytes(b"0" * (audit.FIXTURE_SIZE_LIMIT + 1))
            items = audit.q9_borrowed_fixtures(t)
            self.assertEqual(len(items), 3, items)
            self.assertTrue(any("prod-export-2026.json: named like a production capture" in i for i in items))
            self.assertTrue(any("big.bin: 64 KB data file beside the tests" in i for i in items))
            self.assertTrue(any("test_a.py:2: reads a fixture from outside the test tree" in i for i in items))
            self.assertFalse(any("small-constructed" in i for i in items))

    def test_harness_own_fixtures_are_constructed(self):
        self.assertEqual(audit.q9_borrowed_fixtures(ROOT), [])

    def test_question_nine_is_asked(self):
        self.assertIn("9 fixtures borrowed rather than constructed", [q[0] for q in audit.QUESTIONS])


class Dispositions(unittest.TestCase):
    def test_audit_findings_carry_ids_and_are_dispositioned_through_the_register(self):
        with tree() as t:
            write_config(t)
            templates.render_all(t / ".engine/records")
            write(t, "tests/test_a.py", "def test_x():" + NL + "    assert len(out) > 0" + NL)
            lines, total, could_not = audit.run(t, [])
            self.assertFalse(could_not)
            flagged = [l for l in lines if "[REQUIRES DISPOSITION]" in l]
            self.assertTrue(flagged, lines)
            fid = flagged[0].split()[1]
            self.assertTrue(fid.startswith("AUD-") and len(fid) == 14, fid)
            self.assertTrue(any(f"{total} finding(s); {total} require disposition" in l for l in lines))
            findings.add_check(t, None, id=fid, finding_class="assertions on a class of values", mechanism="audit q4 + review checklist line",
                               lives_in="engine/audit.py", decided_by="Casey")
            lines2, total2, _ = audit.run(t, [])
            self.assertEqual(total2, total)
            self.assertTrue(any(f"{fid} [dispositioned]" in l for l in lines2))
            self.assertTrue(any(f"{total} finding(s); {total - 1} require disposition" in l for l in lines2))

    def test_finding_id_stable_across_line_moves(self):
        a = audit.finding_id("tests/test_a.py:2: asserts a class of values: assert len(out) > 0")
        b = audit.finding_id("tests/test_a.py:9: asserts a class of values: assert len(out) > 0")
        c = audit.finding_id("tests/test_b.py:2: asserts a class of values: assert len(out) > 0")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


class Registry(unittest.TestCase):
    def test_registry_credentials_in_tracked_files_are_findings(self):
        # assembled at run time so the placed copy of this file does not itself trip the scan
        cases = {
            "docker-config.json": '{"auths": {"registry.example.mil": {"au' + 'th": "Y2FzZXk6aHVu' + 'dGVyMjIyMjIyMg=="}}}',
            "ci.sh": "docker lo" + "gin registry.example.mil -u svc -" + "p hunter2hunter2",
            "vars.tf": 'registry_pass' + 'word = "abcdefghijklmnop"',
            "deploy.yml": "ECR_TO" + "KEN: AQoDYXdzEJr1234567890",
        }
        for name, text in cases.items():
            self.assertTrue(credential_scan.scan_text(name, text), name)
        for name, text in {"ci.sh": "docker login registry.example.mil -u svc --password-stdin", "notes.md": "registry password rotated"}.items():
            self.assertEqual(credential_scan.scan_text(name, text), [], name)

    def test_scanner_reads_local_images_and_never_logs_in_or_pulls(self):
        from engine.scan import runner
        from .test_scan import Fake, baseline, project as scan_project
        with tree() as t:
            scan_project(t)
            fake = Fake(baseline(vulns=False))
            sc = runner.Scan(t, None, invoke=fake, engine=("containers", "docker"))
            from .test_scan import cfg as scfg
            sc = runner.Scan(t, scfg(), invoke=fake, engine=("containers", "docker"))
            r = sc.run()
            self.assertEqual(r["verdict"], "green", r["problems"])
            for tool, args, *_ in fake.calls:
                joined = " ".join(args)
                self.assertNotIn("login", joined, (tool, args))
                self.assertNotIn("--username", joined)
                self.assertNotIn("--password", joined)
                if tool != "docker":
                    self.assertNotIn("pull", joined, (tool, args))
                    self.assertNotIn("--registry", joined, (tool, args))
            self.assertFalse(any(tool == "docker" and args[:1] == ["pull"] for tool, args, *_ in fake.calls))


class NoExemption(unittest.TestCase):
    def test_no_supported_way_to_exempt_an_engine_owned_file(self):
        with tree() as t:
            distribute.update(t)
            write_config(t, exempt=[RULES.replace("engine/dist/rules/", ".engine/rules/")], keep_local=[".engine/rules/RULES.md"],
                         preserve=[".engine/rules/RULES.md"], engine_owned_overrides={".engine/rules/RULES.md": True})
            write(t, ".engine/rules/.engine-keep", ".engine/rules/RULES.md" + NL)
            write(t, ".engine/keep", "RULES.md" + NL)
            write(t, ".engine/rules/RULES.md", "# my local edit  engine:keep  engine:exempt  ENGINE-KEEP" + NL)
            s = distribute.update(t)
            self.assertEqual((t / ".engine/rules/RULES.md").read_bytes(), (ROOT / RULES).read_bytes())
            self.assertEqual(s.diverged, [(".engine/rules/RULES.md", ".engine/rules/RULES.md" + own.BACKUP_SUFFIX)])
            # and the same for a shipped hook and a reviewer definition
            for rel in (".engine/hooks/guard.py", ".engine/agents/security-gate.md"):
                write(t, rel, "# kept locally  engine:keep" + NL)
            s = distribute.update(t)
            self.assertEqual(len(s.diverged), 2)
            self.assertEqual((t / ".engine/hooks/guard.py").read_bytes(), (ROOT / "engine/dist/hooks/guard.py").read_bytes())
