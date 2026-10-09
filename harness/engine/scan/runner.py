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
from . import dast, images, nodered, offline

RAW_DIR = ".engine/records/scan/raw"
SBOM_DIR = ".engine/records/scan/sbom"
ACTIONABLE = ".engine/records/scan/actionable.md"
CARRIED_DOC = ".engine/records/scan/carried.md"
CARRIED_RECORD = ".engine/records/carried-findings.md"
DB_VOLUME = ".engine/work/clamav-db"
DATA_DATE = ".engine/records/scan/detection-data-date"
ENGINES = ("containers", "host", "auto")
HIGH = ("HIGH", "CRITICAL")
SEVERITY_RANK = {"UNKNOWN": 0, "NEGLIGIBLE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
SKIP_DIRS = (".engine", ".git")
# static analysis reads the project's own code: not the placed harness, git internals, vendored third-party code
# (scanned by version instead) or the tests (assertions and fixtures are not shipped code)
# a virtualenv and the offline package source hold third-party code the dependency scanners cover (honey-do: bandit read site-packages)
SAST_EXCLUDES = (".engine", ".git", "vendor", "vendored", "third_party", "node_modules", "tests", ".venv", "venv", "offline-packages")
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


# a scan never reaches the network (only `currency` does, spec 04): the scanners' own database and version updates
# are switched off, and trivy resolves nothing from Maven Central. Detection data is refreshed deliberately, and its
# age is gated by check_freshness; a scanner that updated itself mid-scan stalls or fails on a disconnected network.
OFFLINE_ENV = {"TRIVY_SKIP_DB_UPDATE": "true", "TRIVY_SKIP_JAVA_DB_UPDATE": "true", "TRIVY_SKIP_CHECK_UPDATE": "true",
               "TRIVY_OFFLINE_SCAN": "true", "TRIVY_DISABLE_TELEMETRY": "true", "GRYPE_DB_AUTO_UPDATE": "false",
               "GRYPE_CHECK_FOR_APP_UPDATE": "false", "SYFT_CHECK_FOR_APP_UPDATE": "false"}


def real_invoke(root, engine, rt, tool, image, args, mounts=(), timeout=1800):
    """Run a tool under the selected engine. Returns engine.tools.Result."""
    if engine == "containers":
        cmd = ["run", "--rm"]
        for host_path, container_path in mounts:
            cmd += ["-v", f"{host_path}:{container_path}"]
        for k, v in OFFLINE_ENV.items():
            cmd += ["-e", f"{k}={v}"]
        cmd += [image, *args]
        return tools.run_tool(rt, cmd, cwd=str(root), timeout=timeout)
    exe, args = images.HOST_EXECUTABLES.get(tool, tool), list(args)
    # the container command names its program first; on the host that word would be read as a file to scan
    # (hadolint linted a file called "hadolint" and reported a clean Dockerfile that had three violations)
    if args and args[0] in ("clamscan", "freshclam", "hadolint"):
        exe, args = args[0], args[1:]
    return tools.run_tool(exe, args, cwd=str(root), timeout=timeout, env=OFFLINE_ENV)


def package_identity(name):
    """One spelling for a package across scanners. Planted-CVE trials: trivy says PyYAML, Jinja2 and
    org.apache.logging.log4j:log4j-core where grype says pyyaml, jinja2 and log4j-core, so the two never confirmed
    each other and a critical Log4Shell scanned green. Case folded, PEP 503 separators collapsed, a Maven group dropped."""
    n = str(name or "").strip().lower()
    if ":" in n and "/" not in n:          # maven group:artifact (go and npm paths carry slashes, never a colon)
        n = n.rsplit(":", 1)[-1]
    return re.sub(r"[-_.]+", "-", n)


# how many version parts name a runtime's release line: Python 3.14 and Go 1.22 are lines, Node 14 and Java 17 are.
# Planted-CVE trials: Node.js 14.0.0 with a fix in 14.4.0 was carried as "newer series only" and scanned green.
RELEASE_SERIES_DEPTH = {"python": 2, "cpython": 2, "go": 2, "golang": 2, "ruby": 2, "php": 2, "dotnet": 2, ".net": 2,
                        "node": 1, "node.js": 1, "nodejs": 1, "java": 1, "openjdk": 1, "jdk": 1, "jre": 1, "deno": 1, "bun": 1}


def series_depth(name, declared=None):
    """The release-line depth for a runtime: the component's own `series_depth`, else the known value, else 1 (the
    stricter reading: an unknown runtime with a fix anywhere in its major line must take it)."""
    if declared:
        return int(declared)
    return RELEASE_SERIES_DEPTH.get(str(name or "").strip().lower(), 1)


CONDA_ENV = re.compile(r"^(environment|conda[\w.-]*|env)\.ya?ml$", re.I)
REQUIREMENT_INCLUDE = re.compile(r"^(-r|--requirement|-c|--constraint)[\s=]+(\S+)")
PINNED_NAME_VERSION = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*===?\s*([^\s;,]+)")
REQUIREMENTS_FILE = re.compile(r"^requirements[\w.-]*\.(txt|in)$|^constraints[\w.-]*\.txt$", re.I)
# name, optional extras, == or ===, a version; environment markers after ';' allowed
PINNED_REQUIREMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[^\]]*\])?\s*===?\s*[A-Za-z0-9][^\s;,*]*(\s*;.*)?(\s+--.*)?$")
PYPROJECT_DEPENDENCIES = re.compile(r"^\s*(dependencies\s*=\s*\[\s*\S|\[tool\.poetry\.dependencies\]|\[tool\.pdm\])", re.M)
LOCKFILES_FOR = {"package.json": ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml"),
                 "Pipfile": ("Pipfile.lock",), "pyproject.toml": ("poetry.lock", "uv.lock", "pdm.lock"),
                 "Gemfile": ("Gemfile.lock",), "Cargo.toml": ("Cargo.lock",), "composer.json": ("composer.lock",),
                 # neither scanner reads a Gradle build script, only the lockfile (planted build.gradle log4j 2.14.1: green)
                 "build.gradle": ("gradle.lockfile",), "build.gradle.kts": ("gradle.lockfile",)}
# what the second analyzer is per language; a language with none fails the scan (an unread tree is not a clean one)
CODE_LANGUAGES = {".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".ts": "typescript",
                  ".tsx": "typescript", ".jsx": "javascript", ".kt": "kotlin", ".kts": "kotlin", ".java": "java", ".go": "go",
                  ".rb": "ruby", ".php": "php", ".cs": "csharp", ".rs": "rust", ".swift": "swift", ".scala": "scala"}
# TypeScript goes through the same eslint run; the configuration gives it the typescript-eslint parser
SECOND_ANALYZERS = {"python": "bandit", "javascript": "eslint", "typescript": "eslint"}
FLOW_CODE_DIR = ".engine/work/flow-code"
# eslint-plugin-security rules whose finding is a defect, not a smell: they block; the rest are carried
ESLINT_HIGH = frozenset({"detect-eval-with-expression", "detect-child-process", "detect-pseudoRandomBytes",
                         "detect-disable-mustache-escape", "detect-no-csrf-before-method-override", "detect-new-buffer",
                         "detect-buffer-noassert", "detect-bidi-characters"})
UNDECLARED_VENDOR_DIRS = frozenset({"vendor", "vendored", "third_party", "third-party", "thirdparty", "external", "lib-vendor"})
# a line of the licence banner minified libraries carry: "/*! jQuery v1.12.4", "//! moment.js 2.29.1", " * Leaflet 1.9.4",
# " * Chart.js v2.9.3" under a bare "/*!" (planted Chart.js 2.9.3 outside a vendor folder scanned green)
BANNER_LINE = re.compile(r"^[\s/*!]*(?:@preserve|@license)?\s*([A-Za-z][\w.@/-]*(?: [A-Za-z][\w.-]*)?)\s+v?(\d+\.\d+(?:\.\d+)?)\b", re.M)


def npm_installed(nm, seen):
    """SBOM components for the npm packages installed under one node_modules folder (nested ones included)."""
    out = []
    for pj in nm.rglob("package.json"):
        parts = pj.relative_to(nm).parts      # <name>/package.json or @scope/<name>/package.json, at any nesting
        if len(parts) < 2:
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name, version = data.get("name"), data.get("version")
        if not name or not version or not isinstance(name, str):
            continue
        home = pj.parent.parent
        if home.name.startswith("@"):
            home = home.parent
        if home.name != "node_modules" or pj.parent.name != name.split("/")[-1]:
            continue                   # a package.json inside a package's own fixtures or examples, not a package
        if (name, version) in seen:
            continue
        seen.add((name, version))
        purl_name = name.replace("@", "%40", 1) if name.startswith("@") else name
        out.append({"type": "library", "name": name, "version": version, "purl": f"pkg:npm/{purl_name}@{version}"})
    return out


def managed_vendor(vendor_dir, inner):
    """A vendor folder a package manager fills from a lockfile the scanners read: Go's `go mod vendor` (modules.txt
    beside go.mod), Composer's vendor/ (composer.lock), Bundler's vendor/bundle (Gemfile.lock). Not undeclared code."""
    d, parent = pathlib.Path(vendor_dir), pathlib.Path(vendor_dir).parent
    if (d / "modules.txt").is_file() and (parent / "go.mod").is_file():
        return True
    if d.name.lower() == "vendor" and (parent / "composer.lock").is_file():
        return True
    return bool(inner) and inner[0] == "bundle" and (parent / "Gemfile.lock").is_file()


def library_banner(text):
    """(name, version) from the comment a file opens with, or None. Only the opening comment is read: a library
    announces itself there, and a project's own code past it is never mistaken for one."""
    head = text.lstrip("﻿ \t\r\n")
    if head.startswith("/*"):
        end = head.find("*/")
        block = head[:end if end >= 0 else 600]
    elif head.startswith("//"):
        block = "\n".join(l for l in head.splitlines()[:12] if l.lstrip().startswith("//"))
    else:
        return None
    m = BANNER_LINE.search(block)
    if m and m.group(1).strip().lower() != "version":
        return (m.group(1).strip(), m.group(2))
    # the name on one line and "version : 2.29.1" on another (moment.js)
    v = re.search(r"(?i)\bversion\s*[:=]?\s*v?(\d+\.\d+(?:\.\d+)?)\b", block)
    first = next((l.strip(" \t/*!") for l in block.splitlines() if l.strip(" \t/*!")), "")
    name = first.split()[0] if first else ""
    return (name, v.group(1)) if v and name and name.lower() != "version" else None


class Finding:
    def __init__(self, concern, ident, severity="UNKNOWN", package="", version="", fixed=None, target="", source="", reason=None):
        self.concern, self.id, self.severity, self.package, self.version = concern, ident, severity.upper(), package, version
        self.fixed, self.target, self.sources = fixed, target, {source} if source else set()
        self.reason = reason            # why a carried finding is not fixed now: it becomes the POA&M row

    @property
    def key(self):
        return (self.id, package_identity(self.package))

    @property
    def actionable(self):
        if self.reason:                 # explicitly carried: on the plan of action, not blocking
            return False
        return bool(self.fixed) or self.concern in ("malware", "container-hygiene", "iac-misconfiguration", "secret", "sast", "dast")

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
        self.trivy_inventory = None
        self.included_pins = []          # pins from requirements includes the scanners do not open      # None: trivy's tree scan produced nothing to read; set(): it ran and listed these
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
        # dev dependencies run on the build machine (test runners, bundlers): read, not skipped (planted dev-only
        # minimist 1.2.5 scanned green); grype cannot read them, so its silence is coverage, not doubt (unseen_by_grype)
        a = self.run_scanner("vulnerabilities-a", ["fs", "--format", "json", "--scanners", "vuln,secret", "--include-dev-deps", "--list-all-pkgs",
                                                   "--exit-code", "0", *self._skips(target), target], mounts,
                             parse=self._parse_trivy_fs) or []
        excludes = []
        for d in SKIP_DIRS:
            excludes += ["--exclude", f"./{d}/**"]
        b = self.run_scanner("vulnerabilities-b", [f"dir:{target}", "-o", "json", *excludes], mounts,
                             parse=lambda res: self._parse_grype(res, "grype")) or []
        va, vb = self.scan_vendored()
        runtimes = {c["name"].lower(): (c.get("version", ""), c.get("series_depth"))
                    for c in ((self.cfg.get("runtime_components") if self.cfg else None) or [])}
        self.runtime_findings = [self._judge_runtime(f, *runtimes[f.package.lower()]) for f in va + vb if f.package.lower() in runtimes]
        keep = lambda fs: [f for f in fs if f.package.lower() not in runtimes]
        return a + keep(va), b + keep(vb)

    @staticmethod
    def _judge_runtime(f, installed, depth=None):
        """A runtime CVE whose fix exists in the runtime's own release series blocks (upgrade within the series); one
        fixed only in a newer series is carried on the plan of action with that upgrade as its milestone."""
        depth = series_depth(f.package, depth)
        series = ".".join(installed.split(".")[:depth])
        fixes = [v.strip() for v in (f.fixed or "").split(",") if v.strip()]
        same = [v for v in fixes if ".".join(v.split(".")[:depth]) == series]
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
        self.problems += self.undeclared_vendored(declared)
        self.problems += self.unpinned_dependencies()
        source = (self.cfg.get("offline_packages") if self.cfg else None) or offline.DEFAULT_DIR
        dep_files = [f for f in self.root.rglob("*") if f.is_file()
                     and not set(f.relative_to(self.root).parts) & (set(SKIP_DIRS) | {"node_modules", source})]
        self.problems += offline.problems(self.root, dep_files, source)
        installed = self.installed_without_lockfile() + self.included_pins
        if not declared and not runtimes and not installed:
            return None
        comps = list(installed)
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

    def undeclared_vendored(self, declared):
        """Third-party code no declared component covers is invisible to both scanners (planted-CVE trials: jQuery
        1.12.4 dropped into src/static/vendor/ scanned green). Anything under a vendor folder, and any script or
        stylesheet whose banner names a library and version, must be declared; each is a problem until it is."""
        covered = [pathlib.PurePosixPath(c["path"]) for c in declared if c.get("path")]
        skip = set(SKIP_DIRS) | {"node_modules"}            # installed packages are read from their lockfile
        found = {}
        for f in self.root.rglob("*"):
            if not f.is_file():
                continue
            rel = pathlib.PurePosixPath(f.relative_to(self.root).as_posix())
            if set(rel.parts) & skip or any(rel == c or c in rel.parents for c in covered):
                continue
            parts = rel.parts[:-1]
            vend = next((i for i, part in enumerate(parts) if part.lower() in UNDECLARED_VENDOR_DIRS), None)
            if vend is not None and managed_vendor(self.root / pathlib.PurePosixPath(*rel.parts[:vend + 1]), rel.parts[vend + 1:]):
                continue                    # a package manager's vendor folder: its lockfile declares it and is scanned
            if vend is not None:
                where = "/".join(rel.parts[:vend + 2]) if len(parts) > vend + 1 else "/".join(rel.parts[:vend + 1])
                found.setdefault(where, "third-party code under a vendor folder")
                continue
            if f.suffix.lower() in (".js", ".mjs", ".cjs", ".css"):
                try:
                    head = f.read_bytes()[:600].decode("utf-8", "replace")
                except OSError:
                    continue
                lib = library_banner(head)
                if lib:
                    found.setdefault(rel.as_posix(), f"its banner names {lib[0]} {lib[1]}")
        return [f"undeclared third-party code at {where} ({why}): declare it in config vendored_components (name, version, "
                f"purl, path) so it is inventoried and scanned" for where, why in sorted(found.items())]

    def installed_without_lockfile(self):
        """npm packages installed in a node_modules folder no lockfile describes. Neither scanner reads installed
        packages in a directory scan, only lockfiles (planted node_modules/minimist 1.2.5 with no lockfile scanned
        green): the engine reads each package.json and puts the package in the SBOM both scanners check. A runtime
        component with an install_path (Node-RED installed beside the project) has its node_modules read the same way."""
        out, seen = [], set()
        for nm in self.root.rglob("node_modules"):
            rel = nm.relative_to(self.root).parts
            if not nm.is_dir() or set(rel) & set(SKIP_DIRS) or "node_modules" in rel[:-1]:
                continue                       # nested node_modules are read below, from their top folder
            owner = nm.parent
            if any((owner / lock).is_file() for lock in LOCKFILES_FOR["package.json"]):
                continue                       # the lockfile describes it and both scanners read that
            out += npm_installed(nm, seen)
        cfg = getattr(self, "cfg", None)
        for c in (cfg.get("runtime_components") if cfg else None) or []:
            if not c.get("install_path"):
                continue
            nm = pathlib.Path(c["install_path"])
            nm = (nm if nm.is_absolute() else self.root / nm) / "node_modules"
            if not nm.is_dir():
                self.problems.append(f"runtime component {c.get('name')}: install_path {c['install_path']} has no node_modules "
                                     "to inventory: what the runtime ships cannot be scanned")
                continue
            out += npm_installed(nm, seen)
        return out

    def _requirements(self, f, rel, chain=()):
        """Pinning problems in one requirements file, following its -r/-c includes. An included file the scanners do not
        open (they read requirements*.txt only) has its pins put in the SBOM both scanners check (planted
        `-r base.txt` with urllib3 1.24.1 in base.txt scanned green)."""
        out = []
        text = f.read_text(encoding="utf-8", errors="replace").replace("\\\n", " ")
        for line in text.splitlines():
            req = line.split(" #", 1)[0].strip()
            if not req or req.startswith("#"):
                continue
            inc = REQUIREMENT_INCLUDE.match(req)
            if inc:
                target = (f.parent / inc.group(2)).resolve()
                if not target.is_file():
                    out.append(f"{rel} includes {inc.group(2)}, which does not exist: what it pins cannot be checked")
                elif target not in chain + (f.resolve(),) and not REQUIREMENTS_FILE.match(target.name):
                    try:
                        inc_rel = target.relative_to(self.root.resolve()).as_posix()
                    except ValueError:
                        inc_rel = inc.group(2)
                    out += self._requirements(target, inc_rel, chain + (f.resolve(),))
                continue
            if req.startswith("-"):
                continue
            if not PINNED_REQUIREMENT.match(req):
                out.append(f"unpinned dependency in {rel}: '{req.split(' --', 1)[0].strip()}' — a range lets a version "
                           "no scanner checked ship; pin it with == (or install from a lockfile)")
            elif chain:
                m = PINNED_NAME_VERSION.match(req)
                if m:
                    self.__dict__.setdefault("included_pins", []).append({"type": "library", "name": m.group(1), "version": m.group(2),
                                               "purl": f"pkg:pypi/{package_identity(m.group(1))}@{m.group(2)}"})
        return out

    def _conda_environment(self, f, rel):
        """A conda environment file, which neither scanner reads (planted environment.yml pyyaml=5.3 scanned green):
        every package must pin a version, and the pins go into the SBOM both scanners check (conda's Python packages
        carry their PyPI names). The interpreter itself is the declared runtime component."""
        out, in_deps, in_pip = [], False, False
        for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                in_deps, in_pip = line.strip() == "dependencies:", False
                continue
            if not in_deps:
                continue
            item = line.strip()
            if not item.startswith("- "):
                continue
            item = item[2:].strip().strip("'\"")
            if item == "pip:":
                in_pip = True
                continue
            if in_pip and indent <= 2:
                in_pip = False
            m = re.match(r"^(?:[\w.-]+::)?([A-Za-z0-9][A-Za-z0-9._-]*)\s*(==?|=)\s*([0-9][^\s=*]*)$", item)
            if m and not (in_pip and m.group(2) == "="):
                name, version = m.group(1), m.group(3)
                if name.lower() not in ("python", "pip"):
                    self.__dict__.setdefault("included_pins", []).append(
                        {"type": "library", "name": name, "version": version, "purl": f"pkg:pypi/{package_identity(name)}@{version}"})
                continue
            base = re.split(r"[\s=<>~!]", item, 1)[0]
            if base.split("::")[-1].lower() in ("python", "pip"):
                continue
            out.append(f"unpinned dependency in {rel}: '{item}' — a range lets a version no scanner checked ship; "
                       "pin it (name=version, or name==version under pip:)")
        return out

    def unpinned_dependencies(self):
        """A version the scanners cannot know is a version they cannot check (planted-CVE trials: `Jinja2>=2.10` in a
        requirements file scanned green). Every requirement line must pin an exact version, and a manifest that
        resolves versions at install time must have its lockfile beside it."""
        skip = set(SKIP_DIRS) | {"node_modules"}
        out = []
        for f in sorted(self.root.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(self.root).as_posix()
            if set(pathlib.PurePosixPath(rel).parts) & skip:
                continue
            name = f.name
            if REQUIREMENTS_FILE.match(name) and name.lower().endswith(".in") and f.with_suffix(".txt").is_file():
                continue    # pip-tools / `deps lock` input: the .txt beside it is what installs, and it is checked (honey-do)
            if REQUIREMENTS_FILE.match(name):
                out += self._requirements(f, rel)
            elif name in LOCKFILES_FOR:
                if name == "pyproject.toml" and not PYPROJECT_DEPENDENCIES.search(f.read_text(encoding="utf-8", errors="replace")):
                    continue
                if name == "package.json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                    except ValueError:
                        data = {}
                    if not any(data.get(k) for k in ("dependencies", "devDependencies", "optionalDependencies")):
                        continue
                if not any((f.parent / lock).is_file() for lock in LOCKFILES_FOR[name]):
                    out.append(f"{rel} declares dependencies with no lockfile beside it ({' or '.join(LOCKFILES_FOR[name])}): "
                               "the versions that ship are unknown to the scanners")
            elif CONDA_ENV.match(name):
                out += self._conda_environment(f, rel)
            elif name == "Pipfile.lock":
                # neither scanner reads Pipenv's develop section (planted dev-only PyYAML 5.3 scanned green); dev tools run
                # on the build machine, so its pins go into the SBOM both scanners check
                try:
                    develop = json.loads(f.read_text(encoding="utf-8")).get("develop") or {}
                except ValueError:
                    develop = {}
                for pkg_name, spec in develop.items():
                    version = str((spec or {}).get("version", "")).lstrip("=")
                    if version:
                        self.__dict__.setdefault("included_pins", []).append(
                            {"type": "library", "name": pkg_name, "version": version,
                             "purl": f"pkg:pypi/{package_identity(pkg_name)}@{version}"})
            elif f.suffix.lower() in (".csproj", ".fsproj", ".vbproj"):
                # neither scanner reads a .NET project file, only packages.lock.json (planted PackageReference
                # Newtonsoft.Json 12.0.3 in a .csproj scanned green); RestorePackagesWithLockFile writes it
                if "PackageReference" in f.read_text(encoding="utf-8", errors="replace") \
                        and not (f.parent / "packages.lock.json").is_file():
                    out.append(f"{rel} declares dependencies with no lockfile beside it (packages.lock.json; set "
                               "RestorePackagesWithLockFile): the versions that ship are unknown to the scanners")
        return out

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
        if self.trivy_inventory is None:
            self.trivy_inventory = set()
        for r in data.get("Results", []) or []:
            for pk in r.get("Packages", []) or []:          # trivy's inventory: what it could read at all
                self.trivy_inventory.add(package_identity(pk.get("Name", "")))
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
        files = self.own_code_files()
        langs = {}
        for f in files:
            lang = CODE_LANGUAGES.get(f.suffix.lower())
            if lang:
                langs.setdefault(lang, []).append(f)
        # Node-RED: the code inside flows is extracted where both analyzers read it; the settings are checked here
        flows, settings = nodered.find_projects(self.root, files)
        self.flow_code = {}
        if flows:
            flow_dir = self.root / FLOW_CODE_DIR
            shutil.rmtree(flow_dir, ignore_errors=True)
            self.flow_code = nodered.extract_code(self.root, flows, flow_dir)
            if self.flow_code:
                langs.setdefault("javascript", [])
                found = self._semgrep_flow_code(rules, mounts) if rules and pathlib.Path(rules).is_dir() else []
                out += [f for f in found if f.severity != "LOW"]
                info += [f for f in found if f.severity == "LOW"]
        creds = [f for f in files if f.name.endswith("_cred.json")]
        for rule, sev, where, message in nodered.findings(self.root, flows, settings, creds):
            f = Finding("sast", rule, sev, package=where.split("#")[0], target=where, source="node-red")
            if sev == "HIGH":
                f.fixed = "fix the configuration: " + message[:160]
            else:
                f.reason = "Node-RED finding of medium severity: fix or document why it is safe by the milestone"
            (out if sev != "LOW" else info).append(f)
        # the second analyzer is per language, and a language none covers fails the scan: bandit reads only Python, and
        # a Kotlin or JavaScript tree used to pass sast-b clean because it found nothing it could read
        uncovered = sorted(set(langs) - set(SECOND_ANALYZERS))
        for lang in uncovered:
            example = langs[lang][0].relative_to(self.root).as_posix()
            self.problems.append(f"sast: no static analyzer covers the {lang} code ({len(langs[lang])} file(s), e.g. {example}): "
                                 "the scan cannot vouch for code it cannot read")
        complete = not uncovered
        if "python" in langs:
            # bandit's -x never matched on Windows (it reports .\\.engine\\... paths): name the project's own top-level
            # entries as targets instead, and drop anything under an excluded folder when parsing
            own = sorted(p.name for p in self.root.iterdir() if p.name not in SAST_EXCLUDES and not p.name.startswith("."))
            targets = [f"{target}/{n}" if self.engine == "containers" else n for n in own]
            found = self.run_scanner("sast-b-python", ["-q", "-f", "json", "-r", *targets], mounts,
                                     parse=self._parse_bandit, ok_codes=(0,), finding_codes=(1,))
            complete = complete and found is not None
            out += [f for f in found or [] if f.severity != "LOW"]
            info += [f for f in found or [] if f.severity == "LOW"]
        if "javascript" in langs or "typescript" in langs:
            found = self._eslint(langs.get("javascript", []) + langs.get("typescript", []), mounts)
            complete = complete and found is not None
            out += [f for f in found or [] if f.severity != "LOW"]
            info += [f for f in found or [] if f.severity == "LOW"]
        if complete:
            self.ran.append("sast-b")
        self.sast_informational = info
        return out

    def scan_dast(self):
        """The running server probed from outside (scan/dast.py). Not a server: nothing to probe. A server with no
        serve_command fails the scan: code nobody could start is code nobody tested running."""
        files = self.own_code_files()
        flows, settings = nodered.find_projects(self.root, files)
        if not dast.is_server(files, flows or settings):
            self.ran.append("dast")
            return []
        serve = self.cfg.get("serve_command") if self.cfg else None
        if not serve:
            self.problems.append("dast: the project serves HTTP and declares no serve_command (config: the command that starts "
                                 "it, with {port}) — it cannot be probed running, the scan fails")
            return []
        before = len(self.problems)
        problems, found = dast.probe(self.root, serve, (self.cfg.get("protected_routes") or []),
                                     node_red=bool(flows or settings), ready_path=self.cfg.get("serve_ready_path") or "/")
        self.problems += problems
        out = []
        for rule, sev, where, message in found:
            f = Finding("dast", rule, sev, package=where, target=where, source="dast")
            if sev == "HIGH":
                f.fixed = "fix the running behaviour: " + message[:160]
            else:
                f.reason = "dynamic-scan finding of medium severity: fix or document why it is safe by the milestone"
            out.append(f)
        if len(self.problems) == before:
            self.ran.append("dast")
        return out

    def own_code_files(self):
        """The project's own files: not the harness, version control, installed packages, tests or declared vendored code."""
        declared = [pathlib.PurePosixPath(c["path"]) for c in ((self.cfg.get("vendored_components") if self.cfg else None) or [])
                    if c.get("path")]
        skip = set(SKIP_DIRS) | set(SAST_EXCLUDES) | {"node_modules", "__pycache__"}
        out = []
        for f in self.root.rglob("*"):
            if not f.is_file():
                continue
            rel = pathlib.PurePosixPath(f.relative_to(self.root).as_posix())
            if set(rel.parts[:-1]) & skip or any(rel == c or c in rel.parents for c in declared):
                continue
            if rel.name.endswith((".min.js", ".min.css")):
                continue
            out.append(f)
        return out

    def _semgrep_flow_code(self, rules, mounts):
        """Semgrep over code extracted from Node-RED flows (it sits under .engine/work, which the tree scan excludes)."""
        own = pathlib.Path(__file__).resolve().parent.parent / "data" / "semgrep"
        target = f"/src/{FLOW_CODE_DIR}" if self.engine == "containers" else FLOW_CODE_DIR
        cfg_path = "/rules" if self.engine == "containers" else rules
        own_path = "/engine-rules" if self.engine == "containers" else str(own)
        res = self.invoke("semgrep", images.SCANNERS["sast-a"][1], ["scan", "--config", cfg_path, "--config", own_path, "--json",
                                                                   "--metrics", "off", "--disable-version-check", "--quiet", target],
                          mounts + ((rules, "/rules"), (str(own), "/engine-rules")))
        self.raw["semgrep-flows"] = res.stdout
        if not res.ran or res.exit_code not in (0, 1):
            self.problems.append(f"sast-a (semgrep) on Node-RED flow code: fell over (exit {res.exit_code}) — the scan fails")
            return []
        return self._parse_semgrep(res)

    def _eslint(self, js_files, mounts):
        """The second analyzer for JavaScript: eslint with its security plugin, offline (config sast_eslint_config or
        ENGINE_SAST_ESLINT_CONFIG). Returns None when it could not run, which fails the scan."""
        config = (self.cfg.get("sast_eslint_config") if self.cfg else None) or os.environ.get("ENGINE_SAST_ESLINT_CONFIG", "")
        if not config or not pathlib.Path(config).is_file():
            self.problems.append("sast-b (eslint): no configuration (config sast_eslint_config or ENGINE_SAST_ESLINT_CONFIG names "
                                 "the security rule set) — the JavaScript code cannot be analyzed, the scan fails")
            return None
        targets = sorted({f.relative_to(self.root).parts[0] for f in js_files} | ({FLOW_CODE_DIR} if self.flow_code else set()))
        if self.engine == "containers":
            targets = [f"/src/{t}" for t in targets]
        ignores = []
        for d in SAST_EXCLUDES:
            ignores += ["--ignore-pattern", f"**/{d}/**"]
        for c in (self.cfg.get("vendored_components") if self.cfg else None) or []:
            if c.get("path"):
                ignores += ["--ignore-pattern", f"{c['path']}/**"]
        if self.flow_code:
            ignores = [i for i in ignores if i != "**/.engine/**"]
        res = self.invoke("eslint", images.SCANNERS["sast-b-javascript"][1],
                          ["--config", config, "--no-warn-ignored", "-f", "json", *ignores, *targets], mounts)
        self.raw["eslint"] = res.stdout
        if not res.ran or res.exit_code not in (0, 1):
            self.problems.append(f"sast-b-javascript (eslint): fell over (exit {res.exit_code}: {(res.stderr or res.stdout).strip()[:80]})"
                                 " — not skipped, the scan fails")
            return None
        self.ran.append("sast-b-javascript")
        return self._parse_eslint(res)

    def _parse_eslint(self, res):
        try:
            data = json.loads(res.stdout or "[]")
        except ValueError:
            self.problems.append("sast-b (eslint): output is not JSON")
            return None
        out = []
        for f in data:
            for m in f.get("messages", []) or []:
                if m.get("fatal"):
                    # a file the analyzer could not parse is a file nobody analyzed
                    self.problems.append(f"sast-b (eslint): could not parse {self._sast_path(f.get('filePath', ''))}: "
                                         f"{str(m.get('message', ''))[:100]}")
                    continue
                rule = str(m.get("ruleId") or "")
                if not rule.startswith("security/"):
                    continue
                sev = "HIGH" if rule.split("/", 1)[1] in ESLINT_HIGH else "MEDIUM"
                out.append(self._sast_finding(rule.replace("/", "-"), sev, self._sast_path(f.get("filePath", "")), m.get("line", "?"),
                                              m.get("message", ""), "eslint"))
        return [x for x in out if x is not None]

    def _sast_path(self, path):
        """An analyzer's path, relative to the project, with code extracted from a Node-RED flow named by its node."""
        p = str(path).replace("\\", "/")
        try:
            p = pathlib.Path(p).resolve().relative_to(self.root.resolve()).as_posix()
        except (ValueError, OSError):
            pass
        while p.startswith("./"):
            p = p[2:]
        return getattr(self, "flow_code", {}).get(p, p)

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
            out.append(self._sast_finding(x["check_id"].split(".")[-1], sev, self._sast_path(x.get("path", "")), x.get("start", {}).get("line", "?"),
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
            out.append(self._sast_finding(f"{x.get('test_id')}-{x.get('test_name')}", sev, self._sast_path(x.get("filename", "")),
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

    @staticmethod
    def unseen_by_grype(single, sbom_path):
        """A finding trivy alone reports for a package grype never inventoried is not a disagreement between the
        scanners: it is the only scanner that can read that manifest (planted-CVE trials: grype 0.86 does not read a
        NuGet packages.lock.json, so a medium Newtonsoft.Json CVE would have stayed informational). Grype's inventory
        is syft's, the project SBOM."""
        if not sbom_path:
            return []
        try:
            comps = json.loads(pathlib.Path(sbom_path).read_text(encoding="utf-8")).get("components") or []
        except (OSError, ValueError):
            return []
        seen = set()
        for c in comps:
            seen.add(package_identity(c.get("name", "")))
            if c.get("group"):
                seen.add(package_identity(f"{c['group']}:{c.get('name', '')}"))
        return [f for f in single if f.sources == {"trivy"} and package_identity(f.package) not in seen]

    @staticmethod
    def unseen_by_trivy(single, inventory):
        """The mirror of unseen_by_grype: a finding grype alone reports on a package trivy's tree scan never listed
        (planted-CVE trials: a JAR and an installed site-packages folder were read by grype only). When trivy's tree
        scan did not run there is no inventory and nothing is promoted on a guess; when it ran and listed nothing, it
        saw none of these packages (planted site-packages requests 2.25.0 in a stdlib-only app stayed informational)."""
        if inventory is None:
            return []
        return [f for f in single if f.sources == {"grype"} and package_identity(f.package) not in inventory]

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
                if SEVERITY_RANK.get(f.severity, 0) > SEVERITY_RANK.get(merged[f.key].severity, 0):
                    merged[f.key].severity = f.severity          # the scanners disagree: the higher rating stands
            else:
                merged[f.key] = f
        # a high or critical finding one scanner alone reports is not left informational: the scanners' databases
        # differ, and a critical seen once is still critical (fixable it blocks, unfixable it goes on the plan of action)
        confirmed = [f for f in merged.values() if len(f.sources) >= 2 or f.severity in HIGH]
        single = [f for f in merged.values() if not (len(f.sources) >= 2 or f.severity in HIGH)]
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
        from . import alarm
        latest = alarm.latest_rows(self.root)
        existing = {i for i, r in latest.items() if r["status"] != "fixed"}
        owner = (self.cfg.get("scan_owner") if self.cfg else None) or "unassigned"
        days = int((self.cfg.get("carried_review_days") if self.cfg else None) or 90)
        today = datetime.date.today()
        for f in carried:
            ident = f"{f.id}/{f.package}"
            if ident in existing or not (self.root / CARRIED_RECORD).is_file():
                continue
            if ident in latest:                 # closed as fixed, and reported again: the same item reopens
                alarm.resolve(self.root, self.cfg, ident, "carried", note="reported again")
                continue
            table.append(self.root, CARRIED_RECORD, sch.CARRIED, {
                "id": ident, "component": f.package, "version": f.version, "severity": f.severity,
                "reason_no_fix": f.reason or "no upstream fix available at detection", "owner": owner,
                "milestone": "adopt upstream fix when released", "milestone_date": (today + datetime.timedelta(days=days)).isoformat(),
                "review_by": (today + datetime.timedelta(days=days)).isoformat(), "status": "carried",
                "status_history": f"{today.isoformat()}:carried", "side": self.cfg.side if self.cfg else sch.UNKNOWN})

    def close_resolved(self, reported, complete):
        """A carried row whose finding a complete scan no longer reports is closed as fixed, history appended.
        Without this a plan of action only grew: rows written by a scan that read the wrong paths stayed open for ever."""
        if not complete or self.problems or not (self.root / CARRIED_RECORD).is_file():
            return []
        from . import alarm
        still = {f"{f.id}/{f.package}" for f in reported}
        closed = []
        for ident, r in alarm.latest_rows(self.root).items():
            if r["status"] == "carried" and ident not in still:
                alarm.resolve(self.root, self.cfg, ident, "fixed", note="no longer reported by a complete scan")
                closed.append(ident)
        return closed

    def aged_carried(self, findings):
        """REQ-4.10.4–4.10.5: carried findings past review-by, or whose fix has since become available, block."""
        from . import alarm
        rows = list(alarm.latest_rows(self.root).values())     # an item's latest row: a closed one no longer ages
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
        unseen = self.unseen_by_grype(single, self.sbom_project()) + self.unseen_by_trivy(single, self.trivy_inventory)
        confirmed_all += confirmed + unseen
        single_all += [f for f in single if f not in unseen]
        findings += self.secrets
        findings += self.runtime_findings
        findings += self.scan_sast()
        findings += self.scan_dast()
        single_all += self.sast_informational
        findings += confirmed_all
        gate, alarm_verdict, actionable, carried, complete = self.verdicts(findings)
        aged = self.aged_carried(confirmed_all + single_all)
        if aged:
            gate = "red"
        self.route(actionable, carried, single_all)
        self.record_carried(carried)
        closed = self.close_resolved(findings + single_all, complete)
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
                "informational": single_all, "problems": self.problems + self.notes, "aged": aged, "closed": closed, "ran": list(dict.fromkeys(self.ran)), "complete": complete,
                "digests": dict(self.digests), "data_age": self.data_age, "head": head}
