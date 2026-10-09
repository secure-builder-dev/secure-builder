# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Distribution, update and adoption (spec 06).

The harness is a distributable unit separate from any project. `update` places
files into a project according to the four ownership classes; it is idempotent,
report-only on request, performs no version-control action, and never requires a
clean tree. Engine-owned files are overwritten whole with the prior content
preserved beside them and the divergence reported. Seed-if-absent files are
written once. Engine-reference copies are written beside the project's copy
under a suffix. Project-owned paths are never touched. Definitions the engine
placed and has since retired are removed on the strength of a tracking record
the update itself writes; anything the engine did not place is left alone.
"""
import datetime
import hashlib
import json
import pathlib
import subprocess

from . import ownership as own
from . import version

SOURCE_ROOT = pathlib.Path(__file__).resolve().parent.parent   # the harness's own tree
SKIP_NAMES = {"__pycache__", ".pyc"}
SKIP_DIRS_IN_PACKAGE = set()      # the placed harness is the whole package: its self-tests read engine/dist


def sha(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _source_files(source_root, rel):
    """Yield (relative-to-entry, absolute) for a source entry (file or directory)."""
    src = source_root / rel
    if src.is_file():
        yield "", src
        return
    if not src.is_dir():
        return
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        parts = p.relative_to(src).parts
        if any(x in SKIP_NAMES or x.endswith(".pyc") for x in parts):
            continue
        if rel == "engine/" and parts[0] in SKIP_DIRS_IN_PACKAGE:
            continue
        yield p.relative_to(src).as_posix(), p


class Summary:
    def __init__(self):
        self.by_class = {name: {} for name, _ in own.classes()}
        self.diverged = []     # (path, backup)
        self.removed = []      # paths
        self.migrated = []     # (old, new) moved into the four-folder layout
        self.not_migrated = [] # (old, new) left alone because the new path already existed
        self.dry_run = False

    def bump(self, cls, outcome):
        self.by_class[cls][outcome] = self.by_class[cls].get(outcome, 0) + 1

    def lines(self):
        out = [f"update: {'REPORT ONLY — nothing changed' if self.dry_run else 'applied'}"]
        for cls, counts in self.by_class.items():
            desc = ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) or "nothing"
            out.append(f"  {cls}: {desc}")
        if self.diverged:
            out.append(f"  diverged ({len(self.diverged)}) — prior content preserved beside each:")
            out += [f"    - {p} -> {b}" for p, b in self.diverged]
        if self.removed:
            out.append(f"  removed ({len(self.removed)}) — placed by an earlier version, no longer shipped:")
            out += [f"    - {p}" for p in self.removed]
        if self.migrated:
            out.append(f"  layout ({len(self.migrated)}) — moved into the four folders (rules/, harness/, records/, work/):")
            out += [f"    - {a} -> {b}" for a, b in self.migrated]
        if self.not_migrated:
            out.append(f"  layout NOT moved ({len(self.not_migrated)}) — the new path already exists; reconcile by hand:")
            out += [f"    - {a} (new: {b})" for a, b in self.not_migrated]
        return out


# The layout before the four folders (rules/, harness/, records/, work/): old path -> new path.
# A project placed under the old layout is moved, never duplicated; version control sees a rename.
LEGACY_LAYOUT = [
    (f"{own.ENGINE_DIR}/local", f"{own.ENGINE_DIR}/work"),
    (f"{own.ENGINE_DIR}/agents", f"{own.ENGINE_DIR}/rules/agents"),
    (f"{own.ENGINE_DIR}/reference", f"{own.ENGINE_DIR}/rules/reference"),
    (f"{own.ENGINE_DIR}/catalogues", f"{own.ENGINE_DIR}/rules/catalogues"),
    (f"{own.ENGINE_DIR}/models", f"{own.ENGINE_DIR}/rules/models"),
    (f"{own.ENGINE_DIR}/config.json", f"{own.ENGINE_DIR}/rules/config.json"),
    (f"{own.ENGINE_DIR}/control-manifest.json", f"{own.ENGINE_DIR}/rules/control-manifest.json"),
    (f"{own.ENGINE_DIR}/governance.json", f"{own.ENGINE_DIR}/rules/governance.json"),
    (f"{own.ENGINE_DIR}/dependency-policy.json", f"{own.ENGINE_DIR}/rules/dependency-policy.json"),
    (f"{own.ENGINE_DIR}/license-policy.json", f"{own.ENGINE_DIR}/rules/license-policy.json"),
    (f"{own.ENGINE_DIR}/reviewers", f"{own.ENGINE_DIR}/harness/reviewers"),
    (f"{own.ENGINE_DIR}/hooks", f"{own.ENGINE_DIR}/harness/hooks"),
    (f"{own.ENGINE_DIR}/VERSION", f"{own.ENGINE_DIR}/harness/VERSION"),
    (f"{own.ENGINE_DIR}/placed.json", f"{own.ENGINE_DIR}/harness/placed.json"),
    (f"{own.ENGINE_DIR}/CHANGES.md", f"{own.ENGINE_DIR}/harness/CHANGES.md"),
    (f"{own.ENGINE_DIR}/DATA.md", f"{own.ENGINE_DIR}/harness/DATA.md"),
    (f"{own.ENGINE_DIR}/scan", f"{own.ENGINE_DIR}/records/scan"),
    (f"{own.ENGINE_DIR}/detection-data-date", f"{own.ENGINE_DIR}/records/scan/detection-data-date"),
    (f"{own.ENGINE_DIR}/currency-verified", f"{own.ENGINE_DIR}/records/currency-verified"),
    ("AGENTS.md.engine-reference", own.reference_path("AGENTS.md")),
    (f"{own.ENGINE_DIR}/control-manifest.json.engine-reference", own.reference_path(f"{own.ENGINE_DIR}/rules/control-manifest.json")),
    (f"{own.ENGINE_DIR}/governance.json.engine-reference", own.reference_path(f"{own.ENGINE_DIR}/rules/governance.json")),
    (f"{own.ENGINE_DIR}/records/gate-log.md.engine-reference", own.reference_path(f"{own.ENGINE_DIR}/records/gate-log.md")),
]


def migrate_layout(project, dry_run=False):
    """Move a project placed under the old layout into the four folders. Returns the (old, new)
    pairs moved and the pairs left alone: an old path whose new path already exists, or a file
    another process holds open. Tracked paths are moved with `git mv` so history follows them;
    nothing is merged silently."""
    project = pathlib.Path(project)
    moved, kept = [], []
    stuck = []
    tracked = set()
    if (project / ".git").exists():
        res = subprocess.run(["git", "-C", str(project), "ls-files"], capture_output=True, text=True, encoding="utf-8")
        tracked = set(res.stdout.splitlines())
    for old, new in LEGACY_LAYOUT:
        src, dst = project / old, project / new
        if not src.exists():
            continue
        if dst.exists():
            kept.append((old, new))
            continue
        moved.append((old, new))
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if old in tracked or any(t.startswith(old + "/") for t in tracked):
            subprocess.run(["git", "-C", str(project), "mv", "-k", old, new], capture_output=True, text=True)
        if src.exists():            # untracked content, or a whole untracked path: file by file
            try:
                src.rename(dst) if not dst.exists() else _merge_move(src, dst, stuck)
            except OSError:
                _merge_move(src, dst, stuck)
    return moved, kept + [(str(pathlib.Path(x).relative_to(project)).replace("\\", "/"), "held open by another process; move it by hand") for x in stuck]


def _merge_move(src, dst, stuck):
    """Move src's content into dst one file at a time; a file that cannot be moved is left where it
    is and listed, never lost."""
    if src.is_file():
        try:
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.rename(dst)
            else:
                src.unlink()
        except OSError:
            stuck.append(src)
        return
    for child in list(src.iterdir()):
        _merge_move(child, dst / child.name, stuck)
    try:
        src.rmdir()
    except OSError:
        pass


def read_placed(project):
    p = project / own.PLACED_MANIFEST
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return data.get("files", {}) if isinstance(data, dict) else {}


def valid_tracking_entries(lines):
    """REQ-3.5: simple filenames only; anything with a separator or traversal is ignored."""
    out = []
    for raw in lines:
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        if "/" in name or "\\" in name or name in (".", "..") or ".." in name.split("."):
            continue
        if name != pathlib.PurePosixPath(name).name:
            continue
        out.append(name)
    return out


def update(project, source_root=SOURCE_ROOT, dry_run=False):
    project = pathlib.Path(project).resolve()
    source_root = pathlib.Path(source_root).resolve()
    s = Summary()
    s.dry_run = dry_run
    s.migrated, s.not_migrated = migrate_layout(project, dry_run=dry_run)
    placed_before = read_placed(project)
    placed_now = {}

    def put(target, data, cls):
        t = project / target
        existed = t.exists()
        if existed:
            old = t.read_bytes()
            if sha(old) == sha(data):
                s.bump(cls, "unchanged")
                return
            # diverged means edited in place since it was placed: the placed manifest holds the hash of
            # what was written last time. A file that merely changed between harness versions is an
            # upgrade, not a divergence, and leaves no .pre-update copy behind. A file the manifest
            # never recorded is treated as diverged, because nothing proves otherwise.
            if cls == "engine-owned" and placed_before.get(target) != sha(old):
                backup = target + own.BACKUP_SUFFIX
                s.diverged.append((target, backup))
                if not dry_run:
                    (project / backup).write_bytes(old)
        if not dry_run:
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_bytes(data)
        s.bump(cls, "overwritten" if existed else "written")

    # 1. engine-owned: overwrite unconditionally, track, remove stale
    for target, src_rel in own.ENGINE_OWNED.items():
        for sub, abs_src in _source_files(source_root, src_rel):
            tpath = target + sub if target.endswith("/") else target
            data = abs_src.read_bytes()
            put(tpath, data, "engine-owned")
            placed_now[tpath] = sha(data)
    for old_path in sorted(placed_before):
        if old_path not in placed_now and (project / old_path).is_file():
            s.removed.append(old_path)
            s.bump("engine-owned", "removed")
            if not dry_run:
                (project / old_path).unlink()

    # agents tracking record (REQ-3.2–3.5): simple filenames, beside the definitions
    agents_dir = project / own.ENGINE_DIR / "rules" / "agents"
    shipped_agents = sorted(pathlib.PurePosixPath(p).name for p in placed_now
                            if p.startswith(f"{own.ENGINE_DIR}/rules/agents/"))
    record = project / own.TRACKING_RECORD
    if record.is_file():
        for name in valid_tracking_entries(record.read_text(encoding="utf-8").splitlines()):
            if name not in shipped_agents and (agents_dir / name).is_file():
                rel = f"{own.ENGINE_DIR}/rules/agents/{name}"
                if rel not in s.removed:
                    s.removed.append(rel)
                    s.bump("engine-owned", "removed")
                    if not dry_run:
                        (agents_dir / name).unlink()
    if not dry_run:
        agents_dir.mkdir(parents=True, exist_ok=True)
        record.write_text("# definitions placed by the harness; one simple filename per line\n"
                          + "".join(n + "\n" for n in shipped_agents), encoding="utf-8", newline="\n")

    # 2. seed-if-absent (a directory entry seeds each file it holds, individually)
    for target, src_rel in own.SEED_IF_ABSENT.items():
        for sub, abs_src in _source_files(source_root, src_rel):
            t = project / (target + sub if target.endswith("/") else target)
            if t.exists():
                s.bump("seed-if-absent", "already present")
                continue
            s.bump("seed-if-absent", "seeded")
            if not dry_run:
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_bytes(abs_src.read_bytes())

    # 3. engine-reference
    for target, src_rel in own.ENGINE_REFERENCE.items():
        ref = project / own.reference_path(target)
        data = (source_root / src_rel).read_bytes()
        if ref.exists() and sha(ref.read_bytes()) == sha(data):
            s.bump("engine-reference", "unchanged")
        else:
            s.bump("engine-reference", "reference written")
            if not dry_run:
                ref.parent.mkdir(parents=True, exist_ok=True)
                ref.write_bytes(data)

    # 4. project-owned: enumerated, untouched
    s.by_class["project-owned"]["untouched"] = len(own.PROJECT_OWNED)

    # 5. version and placed manifest
    if not dry_run:
        v = version()
        (project / own.VERSION_FILE).parent.mkdir(parents=True, exist_ok=True)
        (project / own.VERSION_FILE).write_text(
            f"{v}\n{datetime.date.today().isoformat()}\n", encoding="utf-8", newline="\n")
        (project / own.PLACED_MANIFEST).write_text(
            json.dumps({"version": v, "files": placed_now}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
    return s


def recorded_version(project):
    p = pathlib.Path(project) / own.VERSION_FILE
    if not p.is_file():
        return None
    lines = p.read_text(encoding="utf-8").splitlines()
    return lines[0].strip() if lines else None


def adopt(project, source_root=SOURCE_ROOT):
    """Adopt the harness into an existing project (spec 06 §7): place files, then
    inventory every file that predates the harness and has never passed a gate.
    Modifies no project source."""
    project = pathlib.Path(project).resolve()
    s = update(project, source_root)
    res = subprocess.run(["git", "-C", str(project), "ls-files"], capture_output=True, text=True)
    files = [f for f in res.stdout.splitlines()
             if f and not f.startswith(own.ENGINE_DIR + "/") and f != "AGENTS.md"] if res.returncode == 0 else []
    inv = project / own.ENGINE_DIR / "records" / "adoption-inventory.md"
    inv.parent.mkdir(parents=True, exist_ok=True)
    if not inv.exists():
        body = ["# Adoption inventory", "",
                f"Generated {datetime.date.today().isoformat()} at adoption. Every file below predates the",
                "harness and has never passed a gate. Each row needs a disposition — reviewed,",
                "accepted (with reason), or scheduled — before the inventory is considered burned down.",
                "Rows are never deleted; dispositions are filled in.", "",
                "| file | disposition | reason |", "|---|---|---|"]
        body += [f"| {f} |  |  |" for f in files]
        inv.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")
    return s, len(files)
