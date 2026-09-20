# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Standing-state probes (spec 01 §9, §7.5; spec 02 §7–8; spec 06 §7.3; spec 04 §10.3).

Everything else in the layer is diff-scoped. These probes look at the whole
head, independent of any change under review:

- the repository state snapshot, keyed by commit, diffed against the previous
  gate's snapshot; every delta receives a disposition, an undispositioned delta
  opens a ticket rather than blocking, and control decay blocks regardless;
- the manifest completeness probe: control-shaped code with no manifest entry,
  as a durable list that converts an unbounded unknown into a finite one;
- the coverage inventory: every source file classified as assessed by a gate,
  never assessed, or assessed elsewhere with evidence not available — with
  "assessed once" never presented as a clean bill of health;
- the adoption inventory's dispositions, and inbound code that reached the
  protected branch without a gate.
"""
import datetime
import json
import pathlib
import re

from . import controlshape, gitutil, lifecycle, manifest
from .outcome import Outcome
from .records import findings as findings_mod
from .records import gatelog, now, table
from .records import schema as sch

SNAPSHOT_DIR = ".engine/local/snapshots"
DELTAS = ".engine/records/standing-state-deltas.md"
UNDECLARED = ".engine/records/undeclared-controls.md"
INVENTORY = ".engine/records/coverage-inventory.md"
ADOPTION = ".engine/records/adoption-inventory.md"
RECEIVED = ".engine/records/received-drops.json"
DECAY = ("ci_runs_tests", "ci_runs_lint", "control_manifest_result", "required_artifacts_present")
ADOPTION_DISPOSITIONS = ("reviewed", "accepted", "scheduled")


# --- 1. repository state snapshot (spec 01 §9.1; spec 02 §7) ---

def measure(root, cfg, test_result=None):
    """The fixed measurement set. Fast; never runs the test suite (the result is passed in)."""
    root = pathlib.Path(root)
    ci_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in root.glob(".github/workflows/*.yml"))
    test_cmd = " ".join(cfg.get("test_command") or []) if cfg else ""
    lint_cmd = " ".join(cfg.get("lint_command") or []) if cfg else ""
    m = {}
    m["ci_runs_tests"] = bool(ci_text) and (("engine check" in ci_text) or (bool(test_cmd) and test_cmd in ci_text) or bool(re.search(r"\b(pytest|npm test|unittest|gradlew test)\b", ci_text)))
    m["ci_runs_lint"] = bool(ci_text) and (("engine check" in ci_text) or (bool(lint_cmd) and lint_cmd in ci_text) or bool(re.search(r"\b(lint|eslint|flake8|ruff)\b", ci_text)))
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else []
    m["deployment_artifact_count"] = len([f for f in files if re.search(r"(^|/)(Dockerfile|docker-compose[^/]*\.ya?ml|deploy/|k8s/|helm/|terraform/|[^/]*\.tf$)", f)])
    m["test_result_counts"] = test_result or "not provided"
    try:
        state, results, structural = manifest.verify(root)
        m["control_manifest_result"] = state
        m["required_artifacts_present"] = all(r["facts"].get("artifact_present", True) for r in results)
    except manifest.ManifestError:
        m["control_manifest_result"] = "absent"
        m["required_artifacts_present"] = True
    m["exported_symbols_without_call_site"] = _uncalled_exports(root, files)
    return m


def _uncalled_exports(root, files):
    root = pathlib.Path(root)
    source = [f for f in files if pathlib.Path(f).suffix in controlshape.SOURCE_EXT and not controlshape.TEST_PATH.search(f) and not f.startswith(".engine/")]
    texts = {f: (root / f).read_text(encoding="utf-8", errors="replace") for f in source if (root / f).is_file()}
    corpus = "\n".join(texts.values())
    count = 0
    for f, text in texts.items():
        for m in re.finditer(r"^(?:export\s+)?(?:def|function|class)\s+([A-Za-z_]\w*)", text, re.M):
            name = m.group(1)
            if name.startswith("_") or name in ("main",):
                continue
            if len(re.findall(r"(?<![\w.])" + re.escape(name) + r"(?![\w])", corpus)) <= 1:
                count += 1
    return count


def snapshot(root, cfg, commit, test_result=None):
    """Capture (idempotent per commit) and return (current, previous, path)."""
    d = pathlib.Path(root) / SNAPSHOT_DIR
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{commit}.json"
    if p.is_file():
        current = json.loads(p.read_text(encoding="utf-8"))
    else:
        current = {"commit": commit, "captured": now(cfg), "measurements": measure(root, cfg, test_result)}
        p.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    others = sorted((x for x in d.glob("*.json") if x != p), key=lambda x: json.loads(x.read_text(encoding="utf-8")).get("captured", ""))
    previous = json.loads(others[-1].read_text(encoding="utf-8")) if others else None
    return current, previous, p


def deltas(current, previous):
    if previous is None:
        return []
    a, b = previous["measurements"], current["measurements"]
    return [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k) and k != "test_result_counts"]


def is_decay(measurement, prev, cur):
    if measurement in ("ci_runs_tests", "ci_runs_lint", "required_artifacts_present"):
        return prev is True and cur is False
    if measurement == "control_manifest_result":
        return prev == "resolved" and cur in ("failed", "invalid")
    return False


def disposition_of(root, commit, measurement):
    rows, _, _ = table.read(root, DELTAS, "standing-state-deltas")
    for r in rows or []:
        if r["commit"].startswith(commit[:12]) and r["measurement"] == measurement and r["disposition"].strip() not in ("", "-", "unknown"):
            return r["disposition"]
    ticket = pathlib.Path(root) / lifecycle.ITEMS_DIR / f"DELTA-{measurement}-{commit[:12]}.md"
    return f"ticket {ticket.stem}" if ticket.is_file() else None


def record_delta(root, cfg, commit, measurement, prev, cur, disposition):
    if not (pathlib.Path(root) / DELTAS).is_file():
        return
    table.append(root, DELTAS, sch.DELTAS, {"date": now(cfg), "commit": commit[:12], "measurement": measurement,
                                            "previous": str(prev), "current": str(cur), "disposition": disposition,
                                            "side": cfg.side if cfg else sch.UNKNOWN})


def run_probe(root, cfg, commit, test_result=None):
    """The probe as an Outcome: deltas dispositioned or ticketed; control decay blocks."""
    name = "standing-state"
    current, previous, _ = snapshot(root, cfg, commit, test_result)
    ds = deltas(current, previous)
    if previous is None:
        return Outcome.nothing_yet(name, "previous snapshot", f"first snapshot captured for {commit[:12]} ({len(current['measurements'])} measurements); nothing to diff yet")
    if not ds:
        return Outcome.clean(name, f"{len(current['measurements'])} measurements unchanged since {previous['commit'][:12]}")
    decay, ticketed, dispositioned = [], [], []
    for k, prev, cur in ds:
        disp = disposition_of(root, commit, k)
        if is_decay(k, prev, cur):
            decay.append(f"{k}: {prev} -> {cur} — control decay blocks even when dispositioned" + (f" ({disp})" if disp else ""))
            record_delta(root, cfg, commit, k, prev, cur, disp or "undispositioned: BLOCKING control decay")
            continue
        if disp:
            dispositioned.append(f"{k}: {prev} -> {cur} ({disp})")
        else:
            item = f"DELTA-{k}-{commit[:12]}"
            if not (pathlib.Path(root) / lifecycle.ITEMS_DIR / f"{item}.md").exists():
                lifecycle.create_item(root, item, "standing-state", f"Delta {k} at {commit[:12]} ({prev} -> {cur}) is dispositioned in the findings register or explained.")
            ticketed.append(f"{k}: {prev} -> {cur} — undispositioned; ticket {item} opened (bookkeeping, not blocking)")
            record_delta(root, cfg, commit, k, prev, cur, f"ticket {item}")
    if decay:
        return Outcome.found(name, f"{len(decay)} control decay delta(s)", decay + ticketed + dispositioned, blocking=True)
    if ticketed:
        return Outcome.found(name, f"{len(ticketed)} delta(s) opened tickets; {len(dispositioned)} dispositioned", ticketed + dispositioned, blocking=False)
    return Outcome.clean(name, f"{len(dispositioned)} delta(s), all dispositioned: " + "; ".join(dispositioned))


# --- 2. manifest completeness probe (spec 01 §7.5) ---

def undeclared_controls(root):
    """Control-shaped symbols in the tree with no manifest entry, using the same detection
    as the completeness-review trigger, applied to the tree."""
    root = pathlib.Path(root)
    try:
        declared = {(c["location"]["file"], c["location"]["symbol"]) for c in manifest.real_controls(manifest.load(root))}
    except manifest.ManifestError:
        declared = set()
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    out = []
    for f in files:
        if pathlib.Path(f).suffix not in controlshape.SOURCE_EXT or controlshape.TEST_PATH.search(f) or f.startswith(".engine/"):
            continue
        p = root / f
        if not p.is_file():
            continue
        for sym, line, fams in controlshape.control_symbols(f, p.read_text(encoding="utf-8", errors="replace")):
            if (f, sym) not in declared:
                out.append({"file": f, "symbol": sym, "line": line, "families": fams})
    return out


def write_undeclared(root, found):
    """Durable list; existing dispositions are kept, new symbols appended, resolved ones marked."""
    p = pathlib.Path(root) / UNDECLARED
    existing = {}
    if p.is_file():
        for l in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| ([^|]+) \| ([^|]+) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$", l)
            if m and m.group(1).strip() not in ("file", "---"):
                existing[(m.group(1).strip(), m.group(2).strip())] = (m.group(4).strip(), m.group(5).strip())
    lines = ["# Undeclared controls", "", "Control-shaped code with no manifest entry (spec 01 §7.5). Each row is dispositioned:",
             "`declared` (a manifest entry now exists) or `not-a-control` with a written reason. The probe does not",
             "block; it makes incompleteness visible.", "", "| file | symbol | families | disposition | reason |", "|---|---|---|---|---|"]
    keys = set()
    for u in found:
        keys.add((u["file"], u["symbol"]))
        disp, reason = existing.get((u["file"], u["symbol"]), ("", ""))
        lines.append(f"| {u['file']} | {u['symbol']} | {', '.join(u['families'])} | {disp} | {reason} |")
    for (f, s), (disp, reason) in existing.items():
        if (f, s) not in keys:
            lines.append(f"| {f} | {s} |  | declared or gone | {reason} |")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return [u for u in found if not existing.get((u["file"], u["symbol"]), ("", ""))[0]]


def completeness_probe(root, cfg):
    name = "manifest-completeness"
    found = undeclared_controls(root)
    if not found and not (pathlib.Path(root) / UNDECLARED).is_file():
        return Outcome.nothing_yet(name, "control-shaped code", "no control-shaped symbol is undeclared")
    pending = write_undeclared(root, found)
    if pending:
        return Outcome.found(name, f"{len(pending)} control-shaped symbol(s) have no manifest entry and no disposition (list: {UNDECLARED})",
                             [f"{u['file']}:{u['line']} {u['symbol']} ({', '.join(u['families'])})" for u in pending], blocking=False)
    return Outcome.clean(name, f"{len(found)} undeclared control-shaped symbol(s), every one dispositioned in {UNDECLARED}")


# --- 3. coverage inventory (spec 01 §9.3; spec 02 §8; spec 04 §10.3) ---

def assessed_files(root, cfg):
    """{file: evidence} from gate-log rows with a passing verdict whose range resolves."""
    rows, _ = gatelog.series(root)
    out = {}
    for r in rows:
        if r["verdict"] not in ("pass",) or r["_superseded"]:
            continue
        m = re.fullmatch(r"([0-9a-f]{7,40})\.\.([0-9a-f]{7,40})", r["range"])
        if not m:
            continue
        base, head = gitutil.rev(root, m.group(1)), gitutil.rev(root, m.group(2))
        side = r.get("side", "")
        if base and head:
            for f in gitutil.changed_files(root, base, head):
                out.setdefault(f, []).append(f"{r['unit']}#{r['run']}" + (f" on side {side}" if cfg and side and side != cfg.side else ""))
    return out


def received_drops(root):
    p = pathlib.Path(root) / RECEIVED
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("drops", [])
    except ValueError:
        return []


def inventory(root, cfg):
    """Classify every tracked source file. Returns (rows, counts)."""
    root = pathlib.Path(root)
    files = [f for f in gitutil.tracked_files(root) if pathlib.Path(f).suffix in controlshape.SOURCE_EXT and not f.startswith(".engine/")]
    assessed = assessed_files(root, cfg)
    elsewhere = set()
    for d in received_drops(root):
        if not d.get("records_transferred"):
            elsewhere.update(d.get("files", []))
        else:   # spec 04 REQ-10.3.2: transferred gate records are evidence of assessment on the other side, recorded as such
            for f, ev in (d.get("assessed") or {}).items():
                assessed.setdefault(f, []).extend(f"{e} on side {d.get('source_side', 'unknown')} (transferred with drop {d.get('bundle_id', '?')})" for e in ev)
    rows, counts = [], {"assessed": 0, "never": 0, "elsewhere": 0}
    for f in files:
        if f in assessed:
            rows.append((f, "assessed", "; ".join(assessed[f])))
            counts["assessed"] += 1
        elif f in elsewhere:
            rows.append((f, "assessed elsewhere, evidence not available", "received across a boundary without its gate records"))
            counts["elsewhere"] += 1
        else:
            rows.append((f, "never assessed", ""))
            counts["never"] += 1
    return rows, counts


def write_inventory(root, cfg):
    rows, counts = inventory(root, cfg)
    total = sum(counts.values()) or 1
    lines = ["# Coverage inventory — the assessed boundary", "",
             f"Generated {datetime.date.today().isoformat()} from the gate log. A file is *assessed* because a passing gate-log",
             "row's range contains it — never because it looks reviewed. 'Assessed' means assessed at least once;",
             "it is not a clean bill of health. *Assessed elsewhere, evidence not available* is code received across",
             "a boundary without its gate records: neither assessed here nor unassessed.", "",
             f"- assessed by a gate: {counts['assessed']} ({counts['assessed'] * 100 // total}%)",
             f"- never assessed: {counts['never']} ({counts['never'] * 100 // total}%)",
             f"- assessed elsewhere, evidence not available: {counts['elsewhere']} ({counts['elsewhere'] * 100 // total}%)", "",
             "| file | state | evidence |", "|---|---|---|"]
    lines += [f"| {f} | {s} | {e} |" for f, s, e in rows]
    p = pathlib.Path(root) / INVENTORY
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return rows, counts


# --- 4. adoption dispositions (spec 06 REQ-7.3) and ungated inbound (spec 02 REQ-4.4.1; spec 01 REQ-12.4) ---

def adoption_problems(root):
    p = pathlib.Path(root) / ADOPTION
    if not p.is_file():
        return None
    out, total = [], 0
    for l in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([^|]+) \| ([^|]*) \| ([^|]*) \|$", l)
        if not m or m.group(1).strip() in ("file", "---"):
            continue
        total += 1
        f, disp, reason = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if disp not in ADOPTION_DISPOSITIONS:
            out.append(f"{f}: no disposition (reviewed, accepted with a reason, or scheduled)")
        elif disp in ("accepted", "scheduled") and not reason:
            out.append(f"{f}: {disp} without a written reason")
    return out, total


def ungated_inbound(root, cfg):
    """Commits on the protected branch not inside any gated range and not recorded as an accepted exception."""
    protected = gitutil.protected_ref(root, cfg.protected_branch if cfg else "main")
    rows, _ = gatelog.series(root)
    if not protected or not rows:
        return None
    gated, bases = set(), []
    for r in rows:
        m = re.fullmatch(r"([0-9a-f]{7,40})\.\.([0-9a-f]{7,40})", r["range"])
        if m and gitutil.rev(root, m.group(1)) and gitutil.rev(root, m.group(2)):
            bases.append(gitutil.rev(root, m.group(1)))
            gated.update(gitutil.commits_in(root, gitutil.rev(root, m.group(1)), gitutil.rev(root, m.group(2))))
    if not bases:
        return None
    # everything that reached the protected branch after the earliest gated base
    earliest = min(bases, key=lambda b: len(gitutil.commits_in(root, b, protected)) * -1)
    since = [c for c in gitutil.git(root, "rev-list", "--no-merges", f"{earliest}..{protected}").stdout.split()]
    a, b, _ = findings_mod.read(root)
    recorded = " ".join(r["risk"] + " " + r["id"] for r in b)
    return [c for c in since if c not in gated and c[:12] not in recorded and c[:7] not in recorded]
