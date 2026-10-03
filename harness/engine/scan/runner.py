# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The scan runner (spec 01 §4.1–4.9; spec 04 §4).

Every external invocation goes through one `invoke` function that a self-test
can replace, and the real one goes through engine.tools with exact exit codes.
Exit-code meaning is per tool and named: for the malware scanner 1 means
detection, 0 means clean, and anything else means the scanner fell over —
which is a different result and never reads as clean.
"""
import datetime
import json
import os
import pathlib
import re
import shutil

from .. import gitutil, stamp, tools
from ..records import now, table
from ..records import schema as sch
from . import images

RAW_DIR = ".engine/records/scan/raw"
SBOM_DIR = ".engine/records/scan/sbom"
ACTIONABLE = ".engine/records/scan/actionable.md"
CARRIED_DOC = ".engine/records/scan/carried.md"
CARRIED_RECORD = ".engine/records/carried-findings.md"
DB_VOLUME = ".engine/work/clamav-db"
DATA_DATE = ".engine/records/scan/detection-data-date"
ENGINES = ("containers", "host", "auto")
HIGH = ("HIGH", "CRITICAL")
SKIP_DIRS = (".engine", ".git")
# static analysis reads the project's own code: not the placed harness, git internals, vendored third-party code
# (scanned by version instead) or the tests (assertions and fixtures are not shipped code)
SAST_EXCLUDES = (".engine", ".git", "vendor", "vendored", "third_party", "node_modules", "tests")
SAST_SEVERITY = {"ERROR": "HIGH", "WARNING": "MEDIUM", "INFO": "LOW"}


class ScanError(Exception):
    pass


def runtime_usable(invoke=None):
    for name in ("docker", "podman"):
        if tools.resolve(name):
            res = tools.run_tool(name, ["info"], timeout=60)
            if res.exit_code == 0:
                return name
    return None


def select_engine(cfg):
    """REQ-4.2.2: containers-only, host-only, or automatic (containers when a runtime is usable)."""
    choice = (cfg.get("scan_engine") if cfg else None) or "auto"
    if choice not in ENGINES:
        raise ScanError(f"scan_engine must be one of {ENGINES}")
    if choice == "containers":
        rt = runtime_usable()
        if not rt:
            raise ScanError("scan_engine is containers-only and no container runtime is usable")
        return "containers", rt
    if choice == "host":
        return "host", None
    rt = runtime_usable()
    return ("containers", rt) if rt else ("host", None)


def real_invoke(root, engine, rt, tool, image, args, mounts=(), timeout=1800):
    """Run a tool under the selected engine. Returns engine.tools.Result."""
    if engine == "containers":
        cmd = ["run", "--rm"]
        for host_path, container_path in mounts:
            cmd += ["-v", f"{host_path}:{container_path}"]
        cmd += [image, *args]
        return tools.run_tool(rt, cmd, cwd=str(root), timeout=timeout)
    exe, args = images.HOST_EXECUTABLES.get(tool, tool), list(args)
    # the container command names its program first; on the host that word would be read as a file to scan
    # (hadolint linted a file called "hadolint" and reported a clean Dockerfile that had three violations)
    if args and args[0] in ("clamscan", "freshclam", "hadolint"):
        exe, args = args[0], args[1:]
    return tools.run_tool(exe, args, cwd=str(root), timeout=timeout)


class Finding:
    def __init__(self, concern, ident, severity="UNKNOWN", package="", version="", fixed=None, target="", source="", reason=None):
        self.concern, self.id, self.severity, self.package, self.version = concern, ident, severity.upper(), package, version
        self.fixed, self.target, self.sources = fixed, target, {source} if source else set()
        self.reason = reason            # why a carried finding is not fixed now: it becomes the POA&M row

    @property
    def key(self):
        return (self.id, self.package)

    @property
    def actionable(self):
        if self.reason:                 # explicitly carried: on the plan of action, not blocking
            return False
        return bool(self.fixed) or self.concern in ("malware", "container-hygiene", "iac-misconfiguration", "secret", "sast")

    def line(self):
        fix = f"fix: {self.fixed}" if self.fixed else "no fix available"
        return f"{self.id} [{self.severity}] {self.package}{'@' + self.version if self.version else ''} ({self.concern}; {fix}; reported by {', '.join(sorted(self.sources))})"


class Scan:
    def __init__(self, root, cfg, invoke=None, engine=None):
        self.root = pathlib.Path(root)
        self.cfg = cfg
        self.mode = cfg.mode if cfg else "local"
        if engine is None:
            engine = select_engine(cfg)
        self.engine, self.rt = engine
        self.invoke = invoke or (lambda tool, image, args, mounts=(): real_invoke(self.root, self.engine, self.rt, tool, image, args, mounts))
        self.raw = {}
        self.ran = []
        self.problems = []
        self.notes = []
        self.findings = []
        self.digests = {}
        self.secrets = []
        self.runtime_findings = []
        self.sast_informational = []
        self.data_age = None
        self.data_date = None

    # --- detection data freshness (§4.4; spec 04 §4.2) ---

    def detection_age_days(self):
        tool, image, _ = images.SCANNERS["malware"]
        if self.mode == "disconnected":
            p = self.root / DATA_DATE
            if not p.is_file():
                return None, "disconnected mode and no detection-data bundle date recorded"
            try:
                d = datetime.date.fromisoformat(p.read_text(encoding="utf-8").strip()[:10])
            except ValueError:
                return None, "detection-data bundle date is unreadable"
            self.data_date = d.isoformat()
            return (datetime.date.today() - d).days, None
        res = self.invoke(tool, image, ["clamscan", "--version"], self._db_mounts())
        m = re.search(r"ClamAV\s+[\d.]+/(\d+)/(.+)$", (res.stdout or "").strip())
        if not m:
            return None, f"detection-data age could not be determined from '{(res.stdout or res.stderr).strip()[:60]}'"
        try:
            d = datetime.datetime.strptime(m.group(2).strip(), "%a %b %d %H:%M:%S %Y").date()
        except ValueError:
            return None, "detection-data date is unparseable"
        self.data_date = d.isoformat()
        return (datetime.date.today() - d).days, None

    def refresh_detection_data(self):
        """REQ-4.4.2: refresh with the tool's own update mechanism, on shared storage."""
        tool, image, _ = images.SCANNERS["malware"]
        (self.root / DB_VOLUME).mkdir(parents=True, exist_ok=True)
        res = self.invoke(tool, image, ["freshclam"], self._db_mounts())
        return res.exit_code == 0

    def _db_mounts(self):
        return ((str(self.root / DB_VOLUME), "/var/lib/clamav"), (str(self.root), "/src"))

    def check_freshness(self, allow_unverified=False):
        threshold = int((self.cfg.get("detection_data_max_age_days") if self.cfg else None) or 7)
        age, why = self.detection_age_days()
        if age is None:
            if allow_unverified:
                self.notes.append(f"malware: {why}; override in effect — verdict marked UNVERIFIED, not clean")
                return "unverified"
            self.problems.append(f"malware: {why}; refusing to report clean (REQ-4.4.4)")
            return "refused"
        if age > threshold:
            if self.mode == "disconnected":
                self.problems.append(f"malware: detection data is {age} day(s) old, threshold {threshold}; disconnected mode cannot refresh — "
                                     "ingest a newer detection-data bundle (the threshold is not relaxed)")
                return "stale"
            if self.refresh_detection_data():
                age, why = self.detection_age_days()
            if age is None or age > threshold:
                self.problems.append(f"malware: detection data is {age if age is not None else 'of unknown age'} day(s) old after refresh, threshold {threshold}")
                return "stale"
        self.data_age = age
        return "fresh"

    # --- images to scan (§4.5) ---

    def ship_images(self):
        declared = self.cfg.get("ship_images") if self.cfg else None
        if declared:
            return dict(declared)
        found = {}
        for wf in sorted(self.root.glob(".github/workflows/*.yml")) + sorted(self.root.glob("deploy/**/*.y*ml")):
            text = wf.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if not re.search(r"docker\s+build\b", line):
                    continue
                mt = re.search(r"-t\s+([\w./-]+(?::[\w.-]+)?)", line)
                mf = re.search(r"-f\s+(\S+)", line)
                if mt:
                    found[mt.group(1).split(":")[0]] = mf.group(1) if mf else "Dockerfile"
        if found:
            return found
        if (self.root / "Dockerfile").is_file():
            return {f"{self.root.name}-app": "Dockerfile"}
        return {}

    def build_images(self, skip_build=False):
        head = gitutil.head(self.root)
        for name, dockerfile in self.ship_images().items():
            if not skip_build:
                res = self.invoke("docker", "", ["build", "--pull", "--no-cache", "-t", name, "-f", dockerfile, "."])
                if res.exit_code != 0:
                    self.problems.append(f"build of {name} failed (exit {res.exit_code})")
                    continue
            insp = self.invoke("docker", "", ["inspect", "--format", "{{.Id}} {{.Created}}", name])
            if insp.exit_code != 0 or not insp.stdout.strip():
                self.problems.append(f"{name}: no image to scan (build skipped: {skip_build})")
                continue
            digest, _, created = insp.stdout.strip().partition(" ")
            if skip_build and not self._created_after_head(created, head):
                self.problems.append(f"{name}: build was skipped and the present image predates the commit under review — refusing to grade a stale artifact (REQ-4.5.3)")
                continue
            self.digests[name] = digest
        return self.digests

    def _created_after_head(self, created, head):
        try:
            img = datetime.datetime.fromisoformat(created.strip().replace("Z", "+00:00")[:26] + "+00:00" if "+" not in created else created.strip().replace("Z", "+00:00"))
        except ValueError:
            return False
        res = gitutil.git(self.root, "show", "-s", "--format=%cI", head)
        try:
            ct = datetime.datetime.fromisoformat(res.stdout.strip())
        except ValueError:
            return False
        return img >= ct

    # --- scanners (§4.1) ---

    def run_scanner(self, concern, args, mounts=(), parse=None, ok_codes=(0,), finding_codes=(1,)):
        tool, image, _ = images.SCANNERS[concern]
        res = self.invoke(tool, image, args, mounts)
        self.raw[tool if concern not in ("vulnerabilities-a", "vulnerabilities-b") else concern] = res.stdout
        if not res.ran or res.exit_code not in tuple(ok_codes) + tuple(finding_codes):
            self.problems.append(f"{concern} ({tool}): fell over (exit {res.exit_code}: {(res.stderr or res.stdout).strip()[:80]}) — not skipped, the scan fails (REQ-4.2.3)")
            return None
        self.ran.append(concern)
        return parse(res) if parse else []

    def scan_hygiene(self):
        dockerfiles = [p for p in self.root.rglob("Dockerfile*") if p.is_file() and ".engine" not in p.parts]
        if not dockerfiles:
            self.ran.append("container-hygiene")
            self.raw["hadolint"] = "[]"
            return []
        args = ["hadolint", "-f", "json", *[str(p.relative_to(self.root)) for p in dockerfiles]]
        return self.run_scanner("container-hygiene", args, ((str(self.root), "/src"),), parse=self._parse_hadolint) or []

    def _parse_hadolint(self, res):
        try:
            items = json.loads(res.stdout or "[]")
        except ValueError:
            return []
        return [Finding("container-hygiene", i.get("code", "DL"), i.get("level", "warning"), target=f"{i.get('file')}:{i.get('line')}",
                        source="hadolint", fixed="follow the rule") for i in items if i.get("level") in ("error", "warning")]

    def scan_iac(self):
        target = "/src" if self.engine == "containers" else "."
        args = ["config", "--format", "json", "--exit-code", "1", *self._skips(target), target]
        return self.run_scanner("iac-misconfiguration", args, ((str(self.root), "/src"),), parse=self._parse_trivy_config) or []

    def _parse_trivy_config(self, res):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            return []
        out = []
        for r in data.get("Results", []) or []:
            for m in r.get("Misconfigurations", []) or []:
                out.append(Finding("iac-misconfiguration", m.get("ID", "MISCONF"), m.get("Severity", "UNKNOWN"),
                                   target=r.get("Target", ""), source="trivy-config", fixed=m.get("Resolution") or "resolve"))
        return out

    def scan_malware(self):
        args = ["clamscan", "-r", "--infected", "/src" if self.engine == "containers" else "."]
        tool, image, _ = images.SCANNERS["malware"]
        res = self.invoke(tool, image, args, self._db_mounts())
        self.raw["clamav"] = res.stdout
        if res.exit_code == 0:
            self.ran.append("malware")
            return []
        if res.exit_code == 1:                      # exactly 1 means detection
            self.ran.append("malware")
            hits = re.findall(r"^(.+?): (.+) FOUND$", res.stdout or "", re.M)
            return [Finding("malware", sig, "CRITICAL", target=path, source="clamav", fixed="remove or quarantine") for path, sig in hits] or \
                   [Finding("malware", "INFECTED", "CRITICAL", source="clamav", fixed="remove or quarantine")]
        self.problems.append(f"malware (clamav): fell over (exit {res.exit_code}) — a container-level failure is not a detection and not a clean result")
        return []

    def scan_vulns(self, name):
        a = self.run_scanner("vulnerabilities-a", ["image", "--format", "json", name], parse=lambda r: self._parse_trivy(r, "trivy"))
        b = self.run_scanner("vulnerabilities-b", [name, "-o", "json"], parse=lambda r: self._parse_grype(r, "grype"))
        return (a or []), (b or [])

    def _parse_trivy(self, res, source):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            return []
        out = []
        for r in data.get("Results", []) or []:
            for v in r.get("Vulnerabilities", []) or []:
                out.append(Finding("vulnerabilities", v.get("VulnerabilityID", "?"), v.get("Severity", "UNKNOWN"),
                                   v.get("PkgName", ""), v.get("InstalledVersion", ""), v.get("FixedVersion") or None, r.get("Target", ""), source))
        return out

    def _parse_grype(self, res, source):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            return []
        out = []
        for m in data.get("matches", []) or []:
            v, a = m.get("vulnerability", {}), m.get("artifact", {})
            fixed = ", ".join(v.get("fix", {}).get("versions", []) or []) or None
            # grype names an advisory by its GHSA id where trivy uses the CVE: key by the CVE alias when there is one,
            # or the two scanners never confirm each other and a real finding stays informational, never blocking
            ident = v.get("id", "?")
            if not ident.startswith("CVE-"):
                ident = next((rv["id"] for rv in m.get("relatedVulnerabilities", []) or [] if str(rv.get("id", "")).startswith("CVE-")), ident)
            out.append(Finding("vulnerabilities", ident, v.get("severity", "UNKNOWN"), a.get("name", ""), a.get("version", ""), fixed, "", source))
        return out

    def _skips(self, target):
        """The placed harness (its own fixtures carry planted secrets) and git internals are not the project."""
        out = []
        for d in SKIP_DIRS:
            out += ["--skip-dirs", f"{target}/{d}" if target != "." else d]
        return out

    def scan_project(self):
        """A project that ships no image is still scanned: its own tree, for vulnerable components (two
        independent scanners, correlated as for images) and committed secrets (antipode and daynight shipped
        no image, so vulnerabilities, secrets and composition were never looked at)."""
        target = "/src" if self.engine == "containers" else "."
        mounts = ((str(self.root), "/src"),)
        a = self.run_scanner("vulnerabilities-a", ["fs", "--format", "json", "--scanners", "vuln,secret", "--exit-code", "0",
                                                   *self._skips(target), target], mounts, parse=self._parse_trivy_fs) or []
        excludes = []
        for d in SKIP_DIRS:
            excludes += ["--exclude", f"./{d}/**"]
        b = self.run_scanner("vulnerabilities-b", [f"dir:{target}", "-o", "json", *excludes], mounts,
                             parse=lambda res: self._parse_grype(res, "grype")) or []
        va, vb = self.scan_vendored()
        runtimes = {c["name"].lower(): c.get("version", "") for c in ((self.cfg.get("runtime_components") if self.cfg else None) or [])}
        self.runtime_findings = [self._judge_runtime(f, runtimes[f.package.lower()]) for f in va + vb if f.package.lower() in runtimes]
        keep = lambda fs: [f for f in fs if f.package.lower() not in runtimes]
        return a + keep(va), b + keep(vb)

    @staticmethod
    def _judge_runtime(f, installed):
        """A runtime CVE whose fix exists in the runtime's own release series blocks (upgrade within the series); one
        fixed only in a newer series is carried on the plan of action with that upgrade as its milestone."""
        series = ".".join(installed.split(".")[:2])
        fixes = [v.strip() for v in (f.fixed or "").split(",") if v.strip()]
        same = [v for v in fixes if ".".join(v.split(".")[:2]) == series]
        if same:
            f.fixed = ", ".join(same)
            return f
        f.reason = (f"fixed only in a newer release series ({', '.join(fixes) or 'none announced'}); "
                    f"no fix in {series}.x — carried until the runtime moves series")
        return f

    def vendored_sbom(self):
        """A CycloneDX inventory of the third-party code the project vendors (config vendored_components:
        name, version, purl, path). A minified library copied in byte-exact carries no package metadata, so
        neither scanner can see it otherwise (antipode and daynight: Leaflet 1.9.4 was invisible to both)."""
        declared = (self.cfg.get("vendored_components") if self.cfg else None) or []
        runtimes = (self.cfg.get("runtime_components") if self.cfg else None) or []
        if any(self.root.rglob("*.py")) and not any(c.get("name", "").lower() == "python" for c in runtimes) \
                and any(p for p in self.root.rglob("*.py") if not set(p.relative_to(self.root).parts) & {".engine", ".git"}):
            self.problems.append("the project runs Python and declares no Python runtime component (config runtime_components): "
                                 "the interpreter is part of what ships and must be inventoried and scanned")
        if not declared and not runtimes:
            return None
        comps = []
        for c in declared:
            path = self.root / c.get("path", "")
            if not c.get("path") or not path.exists():
                self.problems.append(f"vendored component {c.get('name')}: declared path {c.get('path')} does not exist")
                continue
            comps.append({"type": c.get("type", "library"), "name": c["name"], "version": c.get("version", ""),
                          **({"purl": c["purl"]} if c.get("purl") else {})})
        for c in runtimes:
            comps.append({"type": "framework", "name": c["name"], "version": c.get("version", ""),
                          **({"cpe": c["cpe"]} if c.get("cpe") else {}), **({"purl": c["purl"]} if c.get("purl") else {})})
        d = self.root / SBOM_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / "vendored.cdx.json"
        doc = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
               "metadata": {"component": {"type": "application", "name": self.root.name}}, "components": comps}
        p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
        return p

    def scan_vendored(self):
        p = self.vendored_sbom()
        if p is None:
            return [], []
        rel = p.relative_to(self.root).as_posix()
        target = f"/src/{rel}" if self.engine == "containers" else rel
        mounts = ((str(self.root), "/src"),)
        tool_a, image_a, _ = images.SCANNERS["vulnerabilities-a"]
        tool_b, image_b, _ = images.SCANNERS["vulnerabilities-b"]
        ra = self.invoke(tool_a, image_a, ["sbom", "--format", "json", "--exit-code", "0", target], mounts)
        rb = self.invoke(tool_b, image_b, [f"sbom:{target}", "-o", "json"], mounts)
        self.raw["vendored-trivy"], self.raw["vendored-grype"] = ra.stdout, rb.stdout
        for name, res in (("trivy", ra), ("grype", rb)):
            if not res.ran or res.exit_code != 0:
                self.problems.append(f"vendored components ({name}): fell over (exit {res.exit_code}: {(res.stderr or res.stdout).strip()[:80]})")
        return self._parse_trivy(ra, "trivy"), self._parse_grype(rb, "grype")

    def _parse_trivy_fs(self, res):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            return []
        for r in data.get("Results", []) or []:
            for s in r.get("Secrets", []) or []:
                self.secrets.append(Finding("secret", s.get("RuleID", "SECRET"), s.get("Severity", "HIGH"),
                                            target=f"{r.get('Target', '')}:{s.get('StartLine', '?')}", source="trivy-secret",
                                            fixed="remove the secret and rotate it"))
        return self._parse_trivy(res, "trivy")

    def scan_sast(self):
        """Static analysis of the project's own code with two independent analyzers. A HIGH finding blocks, a MEDIUM
        one is carried on the plan of action, a LOW one is informational (an unscanned codebase made the gates moot)."""
        rules = (self.cfg.get("sast_rules") if self.cfg else None) or os.environ.get("ENGINE_SAST_RULES", "")
        target = "/src" if self.engine == "containers" else "."
        mounts = ((str(self.root), "/src"),)
        out, info = [], []
        if not rules or not pathlib.Path(rules).is_dir():
            self.problems.append("sast-a (semgrep): no rule set (config sast_rules or ENGINE_SAST_RULES names a directory of "
                                 "vendored rules) — static analysis cannot run, the scan fails")
        else:
            excludes = []
            for d in SAST_EXCLUDES:
                excludes += ["--exclude", d]
            cfg_path = "/rules" if self.engine == "containers" else rules
            # the engine's own rules run beside the registry's: each one is a defect the registry rules missed
            own = pathlib.Path(__file__).resolve().parent.parent / "data" / "semgrep"
            own_path = "/engine-rules" if self.engine == "containers" else str(own)
            found = self.run_scanner("sast-a", ["scan", "--config", cfg_path, "--config", own_path, "--json", "--metrics", "off",
                                                "--disable-version-check", "--quiet", *excludes, target],
                                     mounts + ((rules, "/rules"), (str(own), "/engine-rules")),
                                     parse=self._parse_semgrep, ok_codes=(0,), finding_codes=(1,)) or []
            out += [f for f in found if f.severity != "LOW"]
            info += [f for f in found if f.severity == "LOW"]
        # bandit's -x never matched on Windows (it reports .\\.engine\\... paths): name the project's own top-level
        # entries as targets instead, and drop anything under an excluded folder when parsing
        own = sorted(p.name for p in self.root.iterdir() if p.name not in SAST_EXCLUDES and not p.name.startswith("."))
        targets = [f"{target}/{n}" if self.engine == "containers" else n for n in own]
        found = self.run_scanner("sast-b", ["-q", "-f", "json", "-r", *targets], mounts,
                                 parse=self._parse_bandit, ok_codes=(0,), finding_codes=(1,)) or [] if targets else []
        if not targets:
            self.ran.append("sast-b")
        out += [f for f in found if f.severity != "LOW"]
        info += [f for f in found if f.severity == "LOW"]
        self.sast_informational = info
        return out

    def _parse_semgrep(self, res):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            self.problems.append("sast-a (semgrep): output is not JSON")
            return []
        for e in data.get("errors", []) or []:
            if e.get("level") == "error":
                self.notes.append(f"sast-a (semgrep): {str(e.get('message', ''))[:120]}")
        out = []
        for x in data.get("results", []) or []:
            extra = x.get("extra", {})
            # only a rule its authors file under security gates: maintainability and correctness rules are read,
            # not enforced (useless-inner-function called a decorator-registered route handler unused)
            security = str((extra.get("metadata") or {}).get("category", "")).lower() == "security"
            sev = SAST_SEVERITY.get(extra.get("severity", ""), "LOW") if security else "LOW"
            out.append(self._sast_finding(x["check_id"].split(".")[-1], sev, x.get("path", ""), x.get("start", {}).get("line", "?"),
                                          extra.get("message", ""), "semgrep"))
        return [f for f in out if f is not None]

    def _parse_bandit(self, res):
        try:
            data = json.loads(res.stdout or "{}")
        except ValueError:
            self.problems.append("sast-b (bandit): output is not JSON")
            return []
        out = []
        for x in data.get("results", []) or []:
            sev = x.get("issue_severity", "LOW").upper()
            if sev == "HIGH" and x.get("issue_confidence", "").upper() == "LOW":
                sev = "MEDIUM"          # a high-severity guess the analyzer itself doubts is carried, not blocking
            out.append(self._sast_finding(f"{x.get('test_id')}-{x.get('test_name')}", sev, x.get("filename", ""),
                                          x.get("line_number", "?"), x.get("issue_text", ""), "bandit"))
        return [f for f in out if f is not None]

    @staticmethod
    def _sast_finding(rule, severity, path, line, message, source):
        path = str(path).replace("\\", "/")
        while path.startswith("./"):           # not lstrip: that would eat the dot of .engine
            path = path[2:]
        if set(path.split("/")[:-1]) & set(SAST_EXCLUDES):
            return None                         # outside the project's own code, whatever the analyzer's exclusions did
        f = Finding("sast", rule, severity, package=path, target=f"{path}:{line}", source=source)
        if severity == "HIGH":
            f.fixed = "fix the code: " + " ".join(str(message).split())[:160]
        elif severity == "MEDIUM":
            f.reason = "static-analysis finding of medium severity: fix or document why it is safe by the milestone"
        return f

    def sbom_project(self):
        tool, image, _ = images.SCANNERS["composition"]
        target = "/src" if self.engine == "containers" else "."
        excludes = []
        for d in SKIP_DIRS:
            excludes += ["--exclude", f"./{d}/**"]
        res = self.invoke(tool, image, [f"dir:{target}", "-o", "cyclonedx-json", *excludes], ((str(self.root), "/src"),))
        if res.exit_code != 0 or not res.stdout.strip():
            self.problems.append(f"composition inventory for the project tree not produced (exit {res.exit_code})")
            return None
        d = self.root / SBOM_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / "project.cdx.json"
        p.write_text(res.stdout, encoding="utf-8", newline="\n")
        return p

    def sbom(self, name):
        tool, image, _ = images.SCANNERS["composition"]
        res = self.invoke(tool, image, [name, "-o", "cyclonedx-json"])
        if res.exit_code != 0 or not res.stdout.strip():
            self.problems.append(f"composition inventory for {name} not produced (exit {res.exit_code})")
            return None
        d = self.root / SBOM_DIR
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{name.replace('/', '_')}.cdx.json"
        p.write_text(res.stdout, encoding="utf-8", newline="\n")
        return p

    # --- correlation, verdicts, routing (§4.6–4.7) ---

    @staticmethod
    def correlate(a, b):
        """Findings both scanners report are confirmed; one-scanner findings are informational."""
        merged = {}
        for f in a + b:
            if f.key in merged:
                merged[f.key].sources |= f.sources
                merged[f.key].fixed = merged[f.key].fixed or f.fixed
            else:
                merged[f.key] = f
        confirmed = [f for f in merged.values() if len(f.sources) >= 2]
        single = [f for f in merged.values() if len(f.sources) < 2]
        return confirmed, single

    def verdicts(self, findings):
        actionable = [f for f in findings if f.actionable]
        carried = [f for f in findings if not f.actionable]
        complete = all(c in self.ran for c in images.REQUIRED_CONCERNS)
        gate = "red" if (actionable or not complete or self.problems) else "green"
        alarm = "red" if any(f.severity in HIGH for f in findings) else "green"
        return gate, alarm, actionable, carried, complete

    def route(self, actionable, carried, informational):
        root = self.root
        act = root / ACTIONABLE
        if actionable:
            act.parent.mkdir(parents=True, exist_ok=True)
            lines = ["# Actionable scan findings", "", "This document exists only while actionable findings exist; its existence blocks the gate.", ""]
            for owner, group in (("application dependencies", [f for f in actionable if f.concern == "vulnerabilities"]),
                                 ("infrastructure definitions", [f for f in actionable if f.concern != "vulnerabilities"])):
                if group:
                    lines += [f"## Owner: {owner}", ""] + [f"- {f.line()}" for f in group] + [""]
            act.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        elif act.exists():
            act.unlink()
        car = root / CARRIED_DOC
        car.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Carried scan findings — risk-acceptance candidates", ""]
        lines += [f"- {f.line()}" for f in carried] or ["(none)"]
        if informational:
            lines += ["", "## Reported by one scanner only (read, not blocking)", ""] + [f"- {f.line()}" for f in informational]
        car.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def record_carried(self, carried):
        """New carried findings become plan-of-action rows (spec 02 REQ-6.3.1; spec 01 REQ-4.10.3)."""
        rows, _, _ = table.read(self.root, CARRIED_RECORD, "carried-findings")
        existing = {r["id"] for r in (rows or [])}
        owner = (self.cfg.get("scan_owner") if self.cfg else None) or "unassigned"
        days = int((self.cfg.get("carried_review_days") if self.cfg else None) or 90)
        today = datetime.date.today()
        for f in carried:
            ident = f"{f.id}/{f.package}"
            if ident in existing or not (self.root / CARRIED_RECORD).is_file():
                continue
            table.append(self.root, CARRIED_RECORD, sch.CARRIED, {
                "id": ident, "component": f.package, "version": f.version, "severity": f.severity,
                "reason_no_fix": f.reason or "no upstream fix available at detection", "owner": owner,
                "milestone": "adopt upstream fix when released", "milestone_date": (today + datetime.timedelta(days=days)).isoformat(),
                "review_by": (today + datetime.timedelta(days=days)).isoformat(), "status": "carried",
                "status_history": f"{today.isoformat()}:carried", "side": self.cfg.side if self.cfg else sch.UNKNOWN})

    def aged_carried(self, findings):
        """REQ-4.10.4–4.10.5: carried findings past review-by, or whose fix has since become available, block."""
        rows, _, _ = table.read(self.root, CARRIED_RECORD, "carried-findings")
        today = datetime.date.today().isoformat()
        now_fixable = {f"{f.id}/{f.package}": f.fixed for f in findings if f.fixed}
        out = []
        for r in rows or []:
            if r["status"] not in ("carried", "detected"):
                continue
            if r["review_by"] < today:
                out.append(f"{r['id']}: carried finding past its review-by date {r['review_by']} — blocking until re-reviewed")
            if r["id"] in now_fixable:
                out.append(f"{r['id']}: an upstream fix is now available ({now_fixable[r['id']]}) — no longer carried, blocking")
        return out

    # --- the whole run ---

    def impossible_here(self):
        """Spec 01 REQ-3.3.2 draws the line between an impossible scan and a failed one. With no
        container runtime and not one scanner on the search path, the scan cannot begin: that
        is impossible, and it is refused before any stamp is written, so the handoff override
        applies. A scanner that is present and falls over is a failed scan, stamped red."""
        if self.engine != "host":
            return None
        import shutil
        present = [tool for tool, _, _ in images.SCANNERS.values() if shutil.which(images.HOST_EXECUTABLES.get(tool, tool))]
        if present:
            return None
        return ("scan impossible here: no container runtime and no scanner on the search path. No stamp is written; "
                "the handoff override for an impossible scan applies (`handoff --scan-impossible \"reason\"`)")

    def run(self, allow_unverified=False, skip_build=False, alarm=False):
        head = gitutil.head(self.root)
        if not head:
            raise ScanError("not a git repository with a commit to scan")
        reason = self.impossible_here()
        if reason:
            raise ScanError(reason)
        freshness = self.check_freshness(allow_unverified=allow_unverified)
        findings = []
        findings += self.scan_hygiene()
        findings += self.scan_iac()
        findings += self.scan_malware()
        confirmed_all, single_all = [], []
        self.build_images(skip_build=skip_build)
        for name in self.digests:
            a, b = self.scan_vulns(name)
            confirmed, single = self.correlate(a, b)
            confirmed_all += confirmed
            single_all += single
            self.sbom(name)
        if not self.digests and self.ship_images():
            self.problems.append("no image could be scanned")
        # the project tree and its vendored components are always scanned, images or not: a Dockerfile whose
        # build was impossible used to switch the tree scan off, and a vulnerable lodash and requests went unread
        a, b = self.scan_project()
        confirmed, single = self.correlate(a, b)
        confirmed_all += confirmed
        single_all += single
        self.sbom_project()
        findings += self.secrets
        findings += self.runtime_findings
        findings += self.scan_sast()
        single_all += self.sast_informational
        findings += confirmed_all
        gate, alarm_verdict, actionable, carried, complete = self.verdicts(findings)
        aged = self.aged_carried(confirmed_all + single_all)
        if aged:
            gate = "red"
        self.route(actionable, carried, single_all)
        self.record_carried(carried)
        raw_dir = self.root / RAW_DIR
        raw_dir.mkdir(parents=True, exist_ok=True)
        for tool, text in self.raw.items():
            (raw_dir / f"{tool}.out").write_text(text or "", encoding="utf-8", newline="\n")
        verdict = "unverified" if freshness == "unverified" and gate == "green" else gate
        if freshness in ("refused", "stale"):
            verdict = "red"
        stamp.write(self.root, commit=head, verdict=verdict, timestamp=now(self.cfg), scanners=list(dict.fromkeys(self.ran)),
                    digests=self.digests, detection_data_date=self.data_date, mode=self.mode)
        return {"verdict": verdict, "alarm": alarm_verdict, "findings": findings, "actionable": actionable, "carried": carried,
                "informational": single_all, "problems": self.problems + self.notes, "aged": aged, "ran": list(dict.fromkeys(self.ran)), "complete": complete,
                "digests": dict(self.digests), "data_age": self.data_age, "head": head}
