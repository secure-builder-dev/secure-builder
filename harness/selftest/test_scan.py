# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The scan subsystem (spec 01 §4; spec 02 §6; spec 04 §4, §10.5). Every tool is
played by a recording fake; nothing here starts a container."""
import datetime
import json
import pathlib
import unittest

from engine import stamp
from engine.checks import artifact_binding, scanner_pins
from engine.config import Config
from engine.outcome import State
from engine.records import table, templates
from engine.records import schema as sch
from engine.scan import alarm, bundles, images, runner
from engine.tools import Result
from .helpers import cli, commit, git_repo, tree, write, write_config

NL = chr(10)
TODAY = datetime.date.today()
FRESH = (TODAY - datetime.timedelta(days=1)).strftime("%a %b %d %H:%M:%S %Y")
STALE = (TODAY - datetime.timedelta(days=40)).strftime("%a %b %d %H:%M:%S %Y")


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local", "side": "low",
         "timezone": "UTC", "ship_images": {"app": "Dockerfile"}, "scan_owner": "casey",
         # static analysis needs a rule directory (any existing one: the fake plays the analyzer) and a Python
         # project declares its runtime
         "sast_rules": str(__import__("pathlib").Path(__file__).resolve().parent),
         "runtime_components": [{"name": "python", "version": "3.12.13", "cpe": "cpe:2.3:a:python:python:3.12.13:*:*:*:*:*:*:*"}]}
    d.update(over)
    return Config(d)


class Fake:
    """A scriptable tool player. Each key is a substring of the tool+args; the value is
    (exit code, stdout). Every call is recorded."""
    def __init__(self, script):
        self.script = script
        self.calls = []

    def __call__(self, tool, image, args, mounts=()):
        self.calls.append((tool, list(args), tuple(mounts)))
        key = tool + " " + " ".join(args)
        for k, (code, out) in self.script.items():
            if k in key:
                return Result(tool, list(args), code, out, "", "fake")
        return Result(tool, list(args), 0, "", "", "fake")


TRIVY = json.dumps({"Results": [{"Target": "app", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-1", "Severity": "HIGH", "PkgName": "libx", "InstalledVersion": "1.0", "FixedVersion": "1.1"},
    {"VulnerabilityID": "CVE-2", "Severity": "LOW", "PkgName": "liby", "InstalledVersion": "2.0"}]}]})
GRYPE = json.dumps({"matches": [
    {"vulnerability": {"id": "CVE-1", "severity": "High", "fix": {"versions": ["1.1"]}}, "artifact": {"name": "libx", "version": "1.0"}},
    {"vulnerability": {"id": "CVE-2", "severity": "Low", "fix": {"versions": []}}, "artifact": {"name": "liby", "version": "2.0"}},
    {"vulnerability": {"id": "CVE-9", "severity": "Medium", "fix": {"versions": []}}, "artifact": {"name": "libz", "version": "3.0"}}]})
CREATED = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).isoformat()


def baseline(fresh=True, vulns=True):
    return {
        "clamscan --version": (0, f"ClamAV 1.4.1/27500/{FRESH if fresh else STALE}" + NL),
        "clamscan -r": (0, "" + NL),
        "hadolint": (0, "[]"),
        "config --format json": (0, json.dumps({"Results": []})),
        "docker build": (0, ""),
        "docker inspect": (0, f"sha256:abc123 {CREATED}"),
        "image --format json": (0, TRIVY if vulns else json.dumps({"Results": []})),
        "app -o json": (0, GRYPE if vulns else json.dumps({"matches": []})),
        "app -o cyclonedx-json": (0, json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "libx"}]})),
        # the project tree is scanned on every run, images or not
        "fs --format json": (0, json.dumps({"Results": []})),
        "grype dir:": (0, json.dumps({"matches": []})),
        "syft dir:": (0, json.dumps({"bomFormat": "CycloneDX", "components": []})),
        "semgrep scan": (0, json.dumps({"results": [], "errors": []})),
        "bandit -q": (0, json.dumps({"results": []})),
        "trivy sbom": (0, json.dumps({"Results": []})),
        "grype sbom:": (0, json.dumps({"matches": []})),
    }


def project(t, **over):
    conf = {"side": "low", "timezone": "UTC", "ship_images": {"app": "Dockerfile"}, "scan_owner": "casey"}
    conf.update(over)
    write_config(t, **conf)
    templates.render_all(t / ".engine/records")
    git_repo(t)
    write(t, "Dockerfile", "FROM scratch" + NL)
    write(t, "src/a.py", "x = 1" + NL)
    head = commit(t, "c")
    return head


class Pins(unittest.TestCase):
    def test_every_reference_pinned_and_embedded_data_on_moving_tag(self):
        self.assertEqual(images.pin_problems(), [])
        self.assertTrue(images.SCANNERS["malware"][2])
        self.assertIs(scanner_pins.run(None, None).state, State.CLEAN)

    def test_digest_pin_on_embedded_data_rejected(self):
        bad = dict(images.SCANNERS); bad["malware"] = ("clamav", "docker.io/clamav/clamav@sha256:" + "0" * 64, True)
        self.assertEqual(images.pin_problems(bad), ["malware (clamav): embedded detection data pinned to a digest — signatures frozen at build time"])

    def test_patch_tag_on_embedded_data_rejected(self):
        bad = dict(images.SCANNERS); bad["malware"] = ("clamav", "docker.io/clamav/clamav:1.4.2", True)
        self.assertEqual(images.pin_problems(bad), ["malware (clamav): embedded detection data pinned to immutable patch tag 1.4.2 — a digest wearing a tag's clothes"])

    def test_unpinned_reference_rejected(self):
        bad = dict(images.SCANNERS); bad["vulnerabilities-a"] = ("trivy", "docker.io/aquasec/trivy", False)
        self.assertEqual(images.pin_problems(bad), ["vulnerabilities-a (trivy): docker.io/aquasec/trivy carries neither a tag nor a digest"])
        import unittest.mock as mock
        with mock.patch.object(images, "SCANNERS", bad):
            o = scanner_pins.run(None, None)
        self.assertIs(o.state, State.FINDINGS)
        self.assertTrue(o.blocking)

    def test_seven_required_concerns_by_separate_tools(self):
        tools_ = [images.SCANNERS[c][0] for c in images.REQUIRED_CONCERNS]
        self.assertEqual(len(images.REQUIRED_CONCERNS), 7, "five plus two static analyzers of the project's own code")
        self.assertEqual(len(set(tools_)), 7)


class Engine(unittest.TestCase):
    def test_three_engine_modes(self):
        self.assertEqual(runner.ENGINES, ("containers", "host", "auto"))
        import unittest.mock as mock
        with mock.patch.object(runner, "runtime_usable", return_value=None):
            self.assertEqual(runner.select_engine(cfg(scan_engine="auto")), ("host", None))
            with self.assertRaises(runner.ScanError):
                runner.select_engine(cfg(scan_engine="containers"))
        with mock.patch.object(runner, "runtime_usable", return_value="docker"):
            self.assertEqual(runner.select_engine(cfg(scan_engine="auto")), ("containers", "docker"))
        self.assertEqual(runner.select_engine(cfg(scan_engine="host")), ("host", None))


class Run(unittest.TestCase):
    def scan(self, t, script, c=None, **kw):
        fake = Fake(script)
        sc = runner.Scan(t, c or cfg(), invoke=fake, engine=("containers", "docker"))
        return sc, sc.run(**kw), fake

    def test_green_scan_writes_stamp_with_digests_sbom_and_no_actionable_document(self):
        with tree() as t:
            head = project(t)
            sc, r, fake = self.scan(t, baseline(vulns=False))
            self.assertEqual(r["verdict"], "green", r["problems"])
            self.assertEqual(sorted(r["ran"]), sorted(images.REQUIRED_CONCERNS))
            st = stamp.read(t)
            self.assertEqual((st["commit"], st["verdict"], st["digests"], st["mode"]), (head, "green", {"app": "sha256:abc123"}, "local"))
            self.assertEqual(stamp.problems(st), [])
            self.assertTrue((t / runner.SBOM_DIR / "app.cdx.json").is_file())
            self.assertFalse((t / runner.ACTIONABLE).exists(), "no actionable findings: the document must not exist")
            self.assertTrue((t / runner.CARRIED_DOC).is_file())
            self.assertTrue((t / runner.RAW_DIR / "clamav.out").is_file())

    def test_rebuild_from_current_tree_without_cache_before_scanning(self):
        with tree() as t:
            project(t)
            sc, r, fake = self.scan(t, baseline(vulns=False))
            build = next(c for c in fake.calls if c[0] == "docker" and c[1][:1] == ["build"])
            self.assertEqual(build[1][:5], ["build", "--pull", "--no-cache", "-t", "app"])
            order = [c[1][0] if c[0] == "docker" else c[0] for c in fake.calls]
            self.assertLess(order.index("build"), order.index("trivy"))

    def test_skipped_build_refuses_stale_image(self):
        with tree() as t:
            project(t)
            script = baseline(vulns=False)
            script["docker inspect"] = (0, "sha256:old 2020-01-01T00:00:00Z")
            sc, r, fake = self.scan(t, script, skip_build=True)
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("refusing to grade a stale artifact" in p for p in r["problems"]), r["problems"])
            self.assertEqual(r["digests"], {})

    def test_two_scanners_correlated_fixable_actionable_unfixable_carried(self):
        with tree() as t:
            project(t)
            sc, r, fake = self.scan(t, baseline())
            self.assertEqual(r["verdict"], "red")
            self.assertEqual([f.id for f in r["actionable"]], ["CVE-1"])
            self.assertEqual([f.id for f in r["carried"]], ["CVE-2"])
            self.assertEqual([f.id for f in r["informational"]], ["CVE-9"], "a one-scanner finding is read, not blocking")
            self.assertTrue((t / runner.ACTIONABLE).is_file())
            self.assertIn("CVE-1 [HIGH] libx@1.0 (vulnerabilities; fix: 1.1; reported by grype, trivy)", (t / runner.ACTIONABLE).read_text())
            rows, _, _ = table.read(t, runner.CARRIED_RECORD, "carried-findings")
            self.assertEqual([(r_["id"], r_["owner"], r_["status"]) for r_ in rows], [("CVE-2/liby", "casey", "carried")])
            self.assertRegex(rows[0]["review_by"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(rows[0]["status_history"].endswith(":carried"))

    def test_gate_and_alarm_verdicts_differ(self):
        with tree() as t:
            project(t)
            script = baseline()
            script["image --format json"] = (0, json.dumps({"Results": [{"Target": "app", "Vulnerabilities": [
                {"VulnerabilityID": "CVE-7", "Severity": "CRITICAL", "PkgName": "p", "InstalledVersion": "1"}]}]}))
            script["app -o json"] = (0, json.dumps({"matches": [{"vulnerability": {"id": "CVE-7", "severity": "Critical", "fix": {"versions": []}},
                                                                 "artifact": {"name": "p", "version": "1"}}]}))
            sc, r, fake = self.scan(t, script)
            self.assertEqual((r["verdict"], r["alarm"]), ("green", "red"), "unfixable critical: carried, not blocking; the alarm fires")

    def test_scanner_that_cannot_run_fails_the_scan(self):
        with tree() as t:
            project(t)
            script = baseline(vulns=False)
            script["hadolint"] = (125, "")
            script["docker build"] = (0, "")
            write(t, "Dockerfile", "FROM scratch" + NL)
            sc, r, fake = self.scan(t, script)
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("container-hygiene (hadolint): fell over (exit 125" in p and "not skipped" in p for p in r["problems"]), r["problems"])
            self.assertNotIn("container-hygiene", r["ran"])

    def test_malware_exit_codes_are_exact(self):
        with tree() as t:
            project(t)
            script = baseline(vulns=False); script["clamscan -r"] = (1, "/src/evil.bin: Eicar-Test-Signature FOUND" + NL)
            sc, r, fake = self.scan(t, script)
            self.assertEqual([f.id for f in r["actionable"]], ["Eicar-Test-Signature"])
            script = baseline(vulns=False); script["clamscan -r"] = (2, "")
            sc, r, fake = self.scan(t, script)
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("malware (clamav): fell over (exit 2)" in p for p in r["problems"]))
            self.assertNotIn("malware", r["ran"])

    def test_stale_detection_data_refreshed_via_tools_own_mechanism_on_shared_storage(self):
        with tree() as t:
            project(t)
            script = baseline(vulns=False)
            versions = iter([(0, f"ClamAV 1.4.1/27000/{STALE}" + NL), (0, f"ClamAV 1.4.1/27500/{FRESH}" + NL)])
            class Seq(Fake):
                def __call__(self, tool, image, args, mounts=()):
                    if args[:2] == ["clamscan", "--version"]:
                        self.calls.append((tool, list(args), tuple(mounts)))
                        code, out = next(versions)
                        return Result(tool, list(args), code, out, "", "fake")
                    return super().__call__(tool, image, args, mounts)
            fake = Seq(script)
            sc = runner.Scan(t, cfg(), invoke=fake, engine=("containers", "docker"))
            r = sc.run()
            self.assertEqual(r["verdict"], "green", r["problems"])
            fresh = next(c for c in fake.calls if c[1] == ["freshclam"])
            self.assertIn((str(t / runner.DB_VOLUME), "/var/lib/clamav"), fresh[2], "refresh and scan share the database volume")
            scan_call = next(c for c in fake.calls if c[1][:2] == ["clamscan", "-r"])
            self.assertIn((str(t / runner.DB_VOLUME), "/var/lib/clamav"), scan_call[2])
            self.assertEqual(r["data_age"], 1)

    def test_undeterminable_data_age_refuses_clean_unless_override_marks_unverified(self):
        with tree() as t:
            project(t)
            script = baseline(vulns=False); script["clamscan --version"] = (0, "garbage")
            sc, r, fake = self.scan(t, script)
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("refusing to report clean" in p for p in r["problems"]))
            sc, r, fake = self.scan(t, script, allow_unverified=True)
            self.assertEqual(r["verdict"], "unverified")
            self.assertEqual(stamp.read(t)["verdict"], "unverified")

    def test_disconnected_mode_uses_bundle_date_and_keeps_threshold(self):
        with tree() as t:
            project(t, mode="disconnected")
            write(t, runner.DATA_DATE, (TODAY - datetime.timedelta(days=30)).isoformat() + NL)
            sc, r, fake = self.scan(t, baseline(vulns=False), c=cfg(mode="disconnected"))
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("disconnected mode cannot refresh" in p and "threshold is not relaxed" in p for p in r["problems"]))
            self.assertFalse(any(c[1] == ["freshclam"] for c in fake.calls), "no refresh attempt in disconnected mode")
            write(t, runner.DATA_DATE, (TODAY - datetime.timedelta(days=2)).isoformat() + NL)
            sc, r, fake = self.scan(t, baseline(vulns=False), c=cfg(mode="disconnected"))
            self.assertEqual(r["verdict"], "green")
            self.assertEqual(r["data_age"], 2)
            self.assertEqual(stamp.read(t)["detection_data_date"], (TODAY - datetime.timedelta(days=2)).isoformat())

    def no_image_project(self, t):
        project(t, ship_images={})
        (t / "Dockerfile").unlink()
        git_repo(t); commit(t, "no dockerfile")

    def test_no_shipped_image_scans_the_project_tree(self):
        # antipode and daynight ship no image; their trees were never scanned for components or secrets
        with tree() as t:
            self.no_image_project(t)
            script = dict(baseline(vulns=False), **{"fs --format json": (0, TRIVY), "grype dir:": (0, GRYPE),
                                                    "syft dir:": (0, json.dumps({"bomFormat": "CycloneDX"}))})
            sc, r, fake = self.scan(t, script, c=cfg(ship_images={}))
            self.assertEqual(r["verdict"], "red", "CVE-1 is confirmed by both scanners and has a fix")
            self.assertIn("CVE-1", [f.id for f in r["actionable"]])
            self.assertEqual([f.id for f in r["informational"]], ["CVE-9"], "one scanner only")
            fs = next(args for tool, args, _ in fake.calls if args[:1] == ["fs"])
            self.assertTrue(any(a.endswith(".engine") for a in fs), "the placed harness is not the project")
            self.assertTrue((t / ".engine/records/scan/sbom/project.cdx.json").is_file())

    def test_a_committed_secret_blocks(self):
        with tree() as t:
            self.no_image_project(t)
            secret = json.dumps({"Results": [{"Target": "src/a.py", "Secrets": [
                {"RuleID": "github-pat", "Severity": "CRITICAL", "Title": "GitHub token", "StartLine": 3}]}]})
            sc, r, fake = self.scan(t, dict(baseline(vulns=False), **{"fs --format json": (0, secret), "syft dir:": (0, "{}")}),
                                    c=cfg(ship_images={}))
            self.assertEqual(r["verdict"], "red")
            self.assertEqual([(f.concern, f.target) for f in r["actionable"]], [("secret", "src/a.py:3")])

    def test_grype_ghsa_ids_correlate_with_trivy_cves(self):
        sc = runner.Scan(".", cfg(), invoke=Fake({}), engine=("host", None))
        trivy = json.dumps({"Results": [{"Target": "x", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-2020-8203", "Severity": "HIGH", "PkgName": "lodash", "InstalledVersion": "4.17.15", "FixedVersion": "4.17.19"}]}]})
        grype = json.dumps({"matches": [{"vulnerability": {"id": "GHSA-p6mc-m468-83gw", "severity": "High", "fix": {"versions": ["4.17.19"]}},
                                         "relatedVulnerabilities": [{"id": "CVE-2020-8203"}], "artifact": {"name": "lodash", "version": "4.17.15"}}]})
        a = sc._parse_trivy(Result("trivy", [], 0, trivy, "", "x"), "trivy")
        b = sc._parse_grype(Result("grype", [], 0, grype, "", "x"), "grype")
        confirmed, single = sc.correlate(a, b)
        self.assertEqual(([f.id for f in confirmed], single), (["CVE-2020-8203"], []))

    def test_declared_vendored_components_are_scanned_by_version(self):
        with tree() as t:
            self.no_image_project(t)
            write(t, "src/static/vendor/leaflet/leaflet.js", "/* leaflet */" + NL)
            vend = [{"name": "leaflet", "version": "1.9.4", "purl": "pkg:npm/leaflet@1.9.4", "path": "src/static/vendor/leaflet"}]
            trivy = json.dumps({"Results": [{"Target": "vendored", "Vulnerabilities": [
                {"VulnerabilityID": "CVE-7", "Severity": "HIGH", "PkgName": "leaflet", "InstalledVersion": "1.9.4", "FixedVersion": "1.9.5"}]}]})
            grype = json.dumps({"matches": [{"vulnerability": {"id": "CVE-7", "severity": "High", "fix": {"versions": ["1.9.5"]}},
                                             "artifact": {"name": "leaflet", "version": "1.9.4"}}]})
            script = dict(baseline(vulns=False), **{"trivy sbom": (0, trivy), "grype sbom:": (0, grype), "syft dir:": (0, "{}")})
            sc, r, fake = self.scan(t, script, c=cfg(ship_images={}, vendored_components=vend))
            self.assertIn(("vulnerabilities", "CVE-7"), [(f.concern, f.id) for f in r["actionable"]])
            doc = json.loads((t / ".engine/records/scan/sbom/vendored.cdx.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["components"][0]["purl"], "pkg:npm/leaflet@1.9.4")

    def test_a_declared_vendored_component_that_is_missing_is_a_problem(self):
        with tree() as t:
            self.no_image_project(t)
            vend = [{"name": "leaflet", "version": "1.9.4", "path": "src/static/vendor/leaflet"}]
            sc, r, fake = self.scan(t, dict(baseline(vulns=False), **{"syft dir:": (0, "{}")}), c=cfg(ship_images={}, vendored_components=vend))
            self.assertEqual(r["verdict"], "red")
            self.assertTrue(any("does not exist" in p for p in r["problems"]), r["problems"])

    def test_sast_high_blocks_medium_is_carried_low_is_informational(self):
        semgrep = json.dumps({"errors": [], "results": [
            {"check_id": "python.lang.security.subprocess-shell-true", "path": "src/app.py", "start": {"line": 4},
             "extra": {"severity": "ERROR", "message": "shell=True with user input", "metadata": {"category": "security"}}},
            {"check_id": "python.lang.audit.eval-detected", "path": "src/app.py", "start": {"line": 5},
             "extra": {"severity": "WARNING", "message": "eval", "metadata": {"category": "security"}}},
            {"check_id": "python.lang.maintainability.useless-inner-function", "path": "src/app.py", "start": {"line": 9},
             "extra": {"severity": "ERROR", "message": "never used", "metadata": {"category": "maintainability"}}}]})
        bandit = json.dumps({"results": [
            {"test_id": "B324", "test_name": "hashlib", "issue_severity": "HIGH", "issue_confidence": "LOW", "filename": "./src/app.py",
             "line_number": 7, "issue_text": "md5"},
            {"test_id": "B404", "test_name": "import_subprocess", "issue_severity": "LOW", "issue_confidence": "HIGH",
             "filename": "./src/app.py", "line_number": 1, "issue_text": "subprocess"},
            {"test_id": "B310", "test_name": "urllib_urlopen", "issue_severity": "HIGH", "issue_confidence": "HIGH",
             "filename": ".\\tests\\test_app.py", "line_number": 3, "issue_text": "urlopen"},
            {"test_id": "B310", "test_name": "urllib_urlopen", "issue_severity": "HIGH", "issue_confidence": "HIGH",
             "filename": ".\\.engine\\harness\\net.py", "line_number": 3, "issue_text": "urlopen"}]})
        with tree() as t:
            self.no_image_project(t)
            sc, r, fake = self.scan(t, dict(baseline(vulns=False), **{"semgrep scan": (0, semgrep), "bandit -q": (1, bandit)}),
                                    c=cfg(ship_images={}))
        self.assertEqual(r["verdict"], "red")
        self.assertEqual([(f.id, f.target) for f in r["actionable"]], [("subprocess-shell-true", "src/app.py:4")])
        carried = {f.id: f.reason for f in r["carried"]}
        self.assertIn("eval-detected", carried)
        self.assertIn("B324-hashlib", carried, "a HIGH the analyzer itself doubts is carried, not blocking")
        self.assertIn("B404-import_subprocess", [f.id for f in r["informational"]])
        self.assertIn("useless-inner-function", [f.id for f in r["informational"]], "a maintainability rule does not gate")
        everything = [f.target for f in r["actionable"] + r["carried"] + r["informational"]]
        self.assertFalse([t for t in everything if t.startswith(("tests/", ".engine/", "engine/"))], "tests and the harness are not the project's code")

    def test_the_engines_own_rules_run_with_every_sast_scan(self):
        own = pathlib.Path(runner.__file__).resolve().parent.parent / "data" / "semgrep"
        self.assertTrue((own / "http-server.yaml").is_file(), "the engine ships its own rules")
        with tree() as t:
            self.no_image_project(t)
            sc, r, fake = self.scan(t, baseline(vulns=False), c=cfg(ship_images={}))
        semgrep = next(args for tool, args, _ in fake.calls if tool == "semgrep")
        self.assertEqual(semgrep.count("--config"), 2, "the vendored registry rules and the engine's own")

    def test_sast_without_a_rule_set_fails_the_scan(self):
        with tree() as t:
            self.no_image_project(t)
            sc, r, fake = self.scan(t, baseline(vulns=False), c=cfg(ship_images={}, sast_rules=str(t / "no-such-rules")))
        self.assertEqual(r["verdict"], "red")
        self.assertTrue(any("no rule set" in p for p in r["problems"]), r["problems"])

    def test_a_python_project_must_declare_its_runtime(self):
        with tree() as t:
            self.no_image_project(t)
            sc, r, fake = self.scan(t, baseline(vulns=False), c=cfg(ship_images={}, runtime_components=[]))
        self.assertTrue(any("declares no Python runtime" in p for p in r["problems"]), r["problems"])

    def test_runtime_cves_block_within_the_series_and_are_carried_across_series(self):
        same = runner.Finding("vulnerabilities", "CVE-A", "HIGH", "python", "3.12.13", "3.13.11, 3.12.14", source="grype")
        newer = runner.Finding("vulnerabilities", "CVE-B", "MEDIUM", "python", "3.12.13", "3.13.11, 3.14.1", source="grype")
        a, b = runner.Scan._judge_runtime(same, "3.12.13"), runner.Scan._judge_runtime(newer, "3.12.13")
        self.assertTrue(a.actionable)
        self.assertEqual(a.fixed, "3.12.14", "the fix within the series is the one to take")
        self.assertFalse(b.actionable)
        self.assertIn("newer release series", b.reason)

    def test_the_host_engine_runs_the_real_executables(self):
        import unittest.mock as mock
        seen = []
        with mock.patch.object(runner.tools, "run_tool", side_effect=lambda exe, args, **k: seen.append((exe, list(args))) or Result(exe, args, 0, "", "", exe)):
            runner.real_invoke(".", "host", None, "clamav", "img", ["clamscan", "-r", "."])
            runner.real_invoke(".", "host", None, "clamav", "img", ["freshclam"])
            runner.real_invoke(".", "host", None, "trivy-config", "img", ["config", "."])
            runner.real_invoke(".", "host", None, "hadolint", "img", ["hadolint", "-f", "json", "Dockerfile"])
        self.assertEqual(seen, [("clamscan", ["-r", "."]), ("freshclam", []), ("trivy", ["config", "."]),
                                ("hadolint", ["-f", "json", "Dockerfile"])], "the program's own name is not a file to lint")

    def test_an_unbuildable_image_does_not_switch_off_the_tree_scan(self):
        # a Dockerfile whose build failed used to skip the tree: a vulnerable lodash and requests went unread
        with tree() as t:
            project(t)
            script = dict(baseline(vulns=False), **{"docker build": (1, ""), "fs --format json": (0, TRIVY), "grype dir:": (0, GRYPE)})
            sc, r, fake = self.scan(t, script)
            self.assertTrue(any(args[:1] == ["fs"] for tool, args, _ in fake.calls), "the tree is scanned")
            self.assertIn("CVE-1", [f.id for f in r["actionable"]])

    def test_a_clean_tree_is_green(self):
        with tree() as t:
            self.no_image_project(t)
            sc, r, fake = self.scan(t, dict(baseline(vulns=False), **{"syft dir:": (0, json.dumps({"bomFormat": "CycloneDX"}))}),
                                    c=cfg(ship_images={}))
            self.assertEqual(r["verdict"], "green", r["problems"])

    def test_ship_images_from_pipeline_definition(self):
        with tree() as t:
            project(t)
            write(t, ".github/workflows/deploy.yml", "run: docker build -t registry/svc-hardened -f deploy/Dockerfile.hardened ." + NL)
            sc = runner.Scan(t, cfg(ship_images=None), invoke=Fake({}), engine=("host", None))
            self.assertEqual(sc.ship_images(), {"registry/svc-hardened": "deploy/Dockerfile.hardened"})


class PlanOfActionClosure(unittest.TestCase):
    """Found on the demo apps: rows written by a scan that read the wrong paths stayed open for ever."""
    def latest(self, t):
        rows, _, _ = table.read(t, runner.CARRIED_RECORD, "carried-findings")
        return {r["id"]: r for r in rows}

    def run_scan(self, t, script, c=None):
        return runner.Scan(t, c or cfg(), invoke=Fake(script), engine=("containers", "docker")).run()

    def test_a_carried_item_no_longer_reported_closes_and_reopens_when_reported_again(self):
        with tree() as t:
            project(t)
            self.run_scan(t, baseline())
            self.assertEqual(self.latest(t)["CVE-2/liby"]["status"], "carried")
            r = self.run_scan(t, baseline(vulns=False))
            self.assertEqual(r["closed"], ["CVE-2/liby"])
            row = self.latest(t)["CVE-2/liby"]
            self.assertEqual(row["status"], "fixed")
            self.assertTrue(row["status_history"].endswith(":fixed (no longer reported by a complete scan)"), row["status_history"])
            r = self.run_scan(t, baseline(vulns=False))
            self.assertEqual(r["closed"], [], "a closed item is closed once")
            self.run_scan(t, baseline())
            row = self.latest(t)["CVE-2/liby"]
            self.assertEqual(row["status"], "carried")
            self.assertTrue(row["status_history"].endswith(":carried (reported again)"), row["status_history"])
            self.assertEqual(sum(1 for r_ in table.read(t, runner.CARRIED_RECORD, "carried-findings")[0]), 3, "history is appended")

    def test_a_scan_with_problems_closes_nothing(self):
        with tree() as t:
            project(t)
            self.run_scan(t, baseline())
            r = self.run_scan(t, baseline(vulns=False), c=cfg(sast_rules=str(t / "no-such-rules")))
            self.assertTrue(r["problems"])
            self.assertEqual(r["closed"], [])
            self.assertEqual(self.latest(t)["CVE-2/liby"]["status"], "carried")

    def test_a_closed_item_does_not_age(self):
        with tree() as t:
            project(t)
            for status, hist in (("carried", "2019-01-01:carried"), ("fixed", "2019-01-01:carried; 2019-02-01:fixed")):
                table.append(t, runner.CARRIED_RECORD, sch.CARRIED, {
                    "id": "CVE-5/libz", "component": "libz", "version": "1", "severity": "LOW", "reason_no_fix": "none", "owner": "casey",
                    "milestone": "m", "milestone_date": "2020-01-01", "review_by": "2020-01-01", "status": status,
                    "status_history": hist, "side": "low"})
            r = self.run_scan(t, baseline(vulns=False))
            self.assertEqual(r["aged"], [])


class Impossible(unittest.TestCase):
    def test_no_runtime_and_no_scanner_is_impossible_not_failed(self):
        """Found by the lifecycle exercise: a scan run where scanning is impossible stamped the
        commit red, and the red stamp then blocked the override meant for exactly that case."""
        import unittest.mock as mock
        with tree() as t:
            project(t)
            sc = runner.Scan(t, cfg(), invoke=Fake({}), engine=("host", None))
            with mock.patch("shutil.which", return_value=None):
                with self.assertRaises(runner.ScanError) as cm:
                    sc.run()
            self.assertIn("scan impossible here", str(cm.exception))
            self.assertIn("No stamp is written", str(cm.exception))
            self.assertIsNone(stamp.read(t))
            # one scanner present and falling over is a failed scan, stamped red, and the override is refused
            sc = runner.Scan(t, cfg(), invoke=Fake({}), engine=("host", None))
            with mock.patch("shutil.which", side_effect=lambda tool: "/usr/bin/trivy" if tool == "trivy" else None):
                r = sc.run()
            self.assertEqual(r["verdict"], "red")
            self.assertEqual(stamp.read(t)["verdict"], "red")


class Aging(unittest.TestCase):
    def test_carried_past_review_by_blocks_and_fix_now_available_blocks(self):
        with tree() as t:
            project(t)
            table.append(t, runner.CARRIED_RECORD, sch.CARRIED, {
                "id": "CVE-2/liby", "component": "liby", "version": "2.0", "severity": "LOW", "reason_no_fix": "none", "owner": "casey",
                "milestone": "m", "milestone_date": "2020-01-01", "review_by": "2020-01-01", "status": "carried",
                "status_history": "2019-01-01:carried", "side": "low"})
            script = baseline()
            script["image --format json"] = (0, json.dumps({"Results": [{"Target": "app", "Vulnerabilities": [
                {"VulnerabilityID": "CVE-2", "Severity": "LOW", "PkgName": "liby", "InstalledVersion": "2.0", "FixedVersion": "2.1"}]}]}))
            script["app -o json"] = (0, json.dumps({"matches": [{"vulnerability": {"id": "CVE-2", "severity": "Low", "fix": {"versions": ["2.1"]}},
                                                                 "artifact": {"name": "liby", "version": "2.0"}}]}))
            sc = runner.Scan(t, cfg(), invoke=Fake(script), engine=("containers", "docker"))
            r = sc.run()
            self.assertEqual(r["verdict"], "red")
            self.assertEqual(r["aged"], ["CVE-2/liby: carried finding past its review-by date 2020-01-01 — blocking until re-reviewed",
                                         "CVE-2/liby: an upstream fix is now available (2.1) — no longer carried, blocking"])


class Alarm(unittest.TestCase):
    def test_alarm_finding_gets_owner_window_record_and_work_item(self):
        with tree() as t:
            project(t)
            f = runner.Finding("vulnerabilities", "CVE-7", "CRITICAL", "p", "1", None, source="trivy")
            raised = alarm.raise_alarms(t, cfg(alarm_triage_days=5), [f])
            self.assertEqual(raised, ["CVE-7/p"])
            rows = alarm.latest_rows(t)
            self.assertEqual((rows["CVE-7/p"]["status"], rows["CVE-7/p"]["owner"]), ("detected", "casey"))
            self.assertEqual(rows["CVE-7/p"]["review_by"], (TODAY + datetime.timedelta(days=5)).isoformat())
            self.assertTrue((t / "tickets/ALARM-CVE-7-p.md").is_file())
            self.assertEqual(alarm.raise_alarms(t, cfg(), [f]), [], "an already-tracked finding is not raised twice")

    def test_resolution_appends_history_and_interval_is_measurable(self):
        with tree() as t:
            project(t)
            f = runner.Finding("vulnerabilities", "CVE-7", "HIGH", "p", "1", None, source="trivy")
            alarm.raise_alarms(t, cfg(), [f])
            v = alarm.resolve(t, cfg(), "CVE-7/p", "fixed", "upgraded p to 2")
            self.assertTrue(v["status_history"].endswith(":fixed (upgraded p to 2)"))
            self.assertTrue(v["status_history"].startswith(f"{TODAY.isoformat()}:detected; "), "the detection entry must be retained")
            rows, _, _ = table.read(t, runner.CARRIED_RECORD, "carried-findings")
            self.assertEqual(len(rows), 2, "a status change is a new row; the old row remains")
            ident, first, resolved, days = alarm.intervals(t)[0]
            self.assertEqual((ident, resolved, days), ("CVE-7/p", TODAY.isoformat(), 0))
            with self.assertRaises(ValueError):
                alarm.resolve(t, cfg(), "CVE-7/p", "ignored")


class Binding(unittest.TestCase):
    def test_digest_mismatch_reported_as_artifact_not_shipped(self):
        with tree() as t:
            write_config(t)
            stamp.write(t, commit="a" * 40, verdict="green", timestamp="x", scanners=["a"], digests={"app": "sha256:aaa"})
            write(t, "deploy/images.lock.json", json.dumps({"app": "sha256:bbb"}))
            o = artifact_binding.run(t, Config({"protected_branch": "main"}))
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.detail, "the artifact under review is not the artifact being shipped")
            self.assertTrue(o.findings[0].startswith("app: the artifact under review (sha256:aaa"))

    def test_matching_digest_is_clean_and_missing_lock_could_not_run(self):
        with tree() as t:
            stamp.write(t, commit="a" * 40, verdict="green", timestamp="x", scanners=["a"], digests={"app": "sha256:aaa"})
            self.assertIs(artifact_binding.run(t, None).state, State.COULD_NOT_RUN)
            write(t, "deploy/images.lock.json", json.dumps({"app": "sha256:aaa"}))
            self.assertIs(artifact_binding.run(t, None).state, State.CLEAN)

    def test_no_stamp_nothing_yet(self):
        with tree() as t:
            self.assertIs(artifact_binding.run(t, None).state, State.NOTHING_YET)


class Stamp(unittest.TestCase):
    def test_stamp_records_commit_verdict_time_scanners_digests_and_no_environment_identifier(self):
        with tree() as t:
            data = stamp.write(t, commit="b" * 40, verdict="green", timestamp="2026-09-20T00:00:00+00:00", scanners=["a", "b"], digests={"app": "sha256:1"})
            self.assertEqual(stamp.problems(data), [])
            self.assertEqual(stamp.problems({"commit": "x", "verdict": "green", "timestamp": "t", "scanners": [], "host": "box1"}),
                             ["stamp carries an environment identifier ('host'); it must not"])
            self.assertIsNone(stamp.for_commit(t, "c" * 40), "a stamp naming a different commit is no stamp")
            self.assertIsNotNone(stamp.for_commit(t, "b" * 40))
            with self.assertRaises(ValueError):
                stamp.write(t, commit="b" * 40, verdict="ok", timestamp="t", scanners=[])


class Bundles(unittest.TestCase):
    def test_data_bundle_round_trip_with_ingest_record(self):
        with tree() as src, tree() as dst:
            project(src); project(dst, mode="disconnected")
            write(src, runner.DB_VOLUME + "/main.cvd", "signatures")
            data = bundles.bundle_data(src, src / "out", cfg(), "alice")
            self.assertEqual(data["kind"], "detection-data")
            self.assertEqual(data["operator"], "alice")
            got = bundles.ingest(dst, src / "out", cfg(mode="disconnected", side="high"), "bob")
            self.assertEqual((dst / runner.DATA_DATE).read_text().strip(), data["produced"])
            self.assertTrue((dst / runner.DB_VOLUME / "main.cvd").is_file())
            rows, _, _ = table.read(dst, bundles.INGEST_RECORD, "ingest-records")
            self.assertEqual((rows[0]["hash_result"], rows[0]["modified_in_transit"], rows[0]["operator"], rows[0]["side"]), ("verified", "no", "bob", "high"))

    def test_hash_mismatch_refused_and_the_two_cases_distinguished(self):
        with tree() as src, tree() as dst:
            project(src); project(dst)
            write(src, runner.DB_VOLUME + "/main.cvd", "signatures")
            bundles.bundle_data(src, src / "out", cfg(), "alice")
            write(src, "out/detection-data.tar", "tampered or filtered")
            with self.assertRaises(RuntimeError) as cm:
                bundles.ingest(dst, src / "out", cfg(), "bob")
            self.assertIn("the boundary filtered the content", str(cm.exception))
            self.assertIn("integrity incident", str(cm.exception))
            rows, _, _ = table.read(dst, bundles.INGEST_RECORD, "ingest-records")
            self.assertTrue(rows[0]["hash_result"].startswith("MISMATCH"))
            self.assertEqual(rows[0]["modified_in_transit"], "unknown — refused")
            self.assertFalse((dst / runner.DATA_DATE).exists(), "a filtered bundle is never ingested on the assumption it was benign")

    def test_image_bundle_records_digests_and_disconnected_never_pulls(self):
        with tree() as t:
            project(t)
            calls = []
            def fake(args):
                calls.append(args)
                if args[0] == "save":
                    write(t, "out/" + args[2].split("/")[-1].split(chr(92))[-1], "tar")
                return Result("docker", args, 0, "sha256:" + "d" * 64 if args[0] == "image" else "", "", "fake")
            data = bundles.bundle_images(t, t / "out", cfg(), "alice", invoke=fake)
            self.assertEqual(len(data["files"]), len(images.SCANNERS))
            self.assertTrue(all(v["digest"].startswith("sha256:") for v in data["files"].values()))
            with self.assertRaises(RuntimeError):
                bundles.bundle_images(t, t / "out2", cfg(mode="disconnected"), "alice", invoke=fake)
            missing = bundles.images_present(invoke=lambda args: Result("docker", args, 1, "", "", "fake"))
            self.assertEqual(len(missing), len(images.SCANNERS))
            self.assertIn("a missing image is a failure, never a skip", missing[0])


class Coverage9(unittest.TestCase):
    """Fixtures the receipts showed were missing (spec 05 REQ-3.4: fix the test, not the code)."""

    def test_containers_engine_invokes_docker_run_with_pinned_image(self):
        import os
        from .stubs import invocations, stub_path, stub_tool
        with tree() as t:
            stub_tool(t / "bin", "docker", exit_code=0, stdout="ok")
            old = os.environ.get("PATH", "")
            os.environ["PATH"] = stub_path(t / "bin")
            try:
                res = runner.real_invoke(t, "containers", "docker", "hadolint", "img:1", ["hadolint", "-f", "json"], ((str(t), "/src"),))
            finally:
                os.environ["PATH"] = old
            self.assertEqual(res.exit_code, 0)
            self.assertEqual(invocations(t / "bin"), [f"docker run --rm -v {t}:/src img:1 hadolint -f json"])

    def test_incomplete_scanner_set_fails_gate_independent_of_findings(self):
        with tree() as t:
            project(t)
            sc = runner.Scan(t, cfg(), invoke=Fake({}), engine=("host", None))
            sc.ran = ["malware"]
            gate, alarm_, actionable, carried, complete = sc.verdicts([])
            self.assertEqual((gate, complete, actionable), ("red", False, []))
            sc.ran = list(images.REQUIRED_CONCERNS)
            self.assertEqual(sc.verdicts([])[0], "green")

    def test_actionable_document_routes_by_owning_surface(self):
        with tree() as t:
            project(t)
            script = baseline()
            script["hadolint"] = (1, json.dumps([{"code": "DL3007", "level": "warning", "file": "Dockerfile", "line": 1}]))
            sc = runner.Scan(t, cfg(), invoke=Fake(script), engine=("containers", "docker"))
            sc.run()
            lines = (t / runner.ACTIONABLE).read_text(encoding="utf-8").splitlines()
            self.assertIn("## Owner: application dependencies", lines)
            self.assertIn("## Owner: infrastructure definitions", lines)
            self.assertLess(lines.index("## Owner: application dependencies"), lines.index("- CVE-1 [HIGH] libx@1.0 (vulnerabilities; fix: 1.1; reported by grype, trivy)"))

    def test_stamp_requires_commit_and_records_which_scanners_ran(self):
        self.assertIn("stamp lacks 'commit'", stamp.problems({"verdict": "green", "timestamp": "t", "scanners": []}))
        with tree() as t:
            project(t)
            script = baseline(vulns=False); script["hadolint"] = (125, "")
            sc = runner.Scan(t, cfg(), invoke=Fake(script), engine=("containers", "docker"))
            r = sc.run()
            self.assertEqual(stamp.read(t)["scanners"], r["ran"])
            self.assertNotIn("container-hygiene", stamp.read(t)["scanners"], "a partial scan is visible as partial")

    def test_carried_row_is_a_plan_of_action_record(self):
        with tree() as t:
            project(t)
            sc = runner.Scan(t, cfg(carried_review_days=30), invoke=Fake(baseline()), engine=("containers", "docker"))
            sc.run()
            rows, _, _ = table.read(t, runner.CARRIED_RECORD, "carried-findings")
            r = rows[0]
            self.assertEqual(r["milestone"], "adopt upstream fix when released")
            self.assertEqual(r["milestone_date"], (TODAY + datetime.timedelta(days=30)).isoformat())
            self.assertEqual(r["reason_no_fix"], "no upstream fix available at detection")
            self.assertEqual((r["component"], r["version"], r["severity"]), ("liby", "2.0", "LOW"))

    def test_aged_carried_finding_alone_makes_the_gate_red(self):
        with tree() as t:
            project(t)
            table.append(t, runner.CARRIED_RECORD, sch.CARRIED, {
                "id": "CVE-8/libq", "component": "libq", "version": "1", "severity": "LOW", "reason_no_fix": "none", "owner": "casey",
                "milestone": "m", "milestone_date": "2020-01-01", "review_by": "2020-01-01", "status": "carried",
                "status_history": "2019-01-01:carried", "side": "low"})
            sc = runner.Scan(t, cfg(), invoke=Fake(baseline(vulns=False)), engine=("containers", "docker"))
            r = sc.run()
            self.assertEqual(r["problems"], [])
            self.assertEqual(r["verdict"], "red", "an aged carried finding blocks even when the scan itself is clean")
