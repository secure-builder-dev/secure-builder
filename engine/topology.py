# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Two-instance topology (spec 04 §10): development across a one-way domain boundary.

Not a mode. Two harness instances, a low side where the work happens and a high
side that receives code through a gatekeeper. The side where the work happened
owns the record; nothing is merged silently across the boundary; the high
side's record set is the deliverable one; what crosses is enumerated and
nothing depends on a return path; a change that originates on the high side is
recorded with its back-port status, counted at every gate, and gated like any
other; every crossing produces an ingest record.
"""
import datetime
import hashlib
import json
import pathlib
import tarfile

from . import gitutil, probes
from .records import gatelog, now, table
from .records import schema as sch

DIVERGENCE = ".engine/records/high-side-changes.md"
INGEST_RECORD = ".engine/records/ingest-records.md"
RECEIVED = probes.RECEIVED
SIDES = ("low", "high")

# REQ-10.1.1 / 10.1.2: which side is authoritative for each artifact class (spec 02 §2).
PRODUCING_SIDE = "the side where the work happened"
AUTHORITY = [
    ("gate log", PRODUCING_SIDE, "low-side gates produce low-side rows; high-side gates produce high-side rows"),
    ("findings register", PRODUCING_SIDE, "a disposition is recorded where it was decided"),
    ("governance changelog", PRODUCING_SIDE, "a rule change is recorded where it was approved"),
    ("carried findings / plan of action", PRODUCING_SIDE, "the side whose scan carried it"),
    ("standing-state deltas", PRODUCING_SIDE, "measured per instance; never compared across sides"),
    ("coverage inventory", "each side for its own tree", "the high side classifies received code itself (§10.3)"),
    ("scan artifacts and stamp", PRODUCING_SIDE, "a scan describes the tree it ran on"),
    ("mutation results", PRODUCING_SIDE, ""),
    ("control manifest", "low side", "declared where the code is written; crosses with the source"),
    ("configuration", "each side for itself", "two instances, two configurations"),
    ("catalogues, detection data, scanner images", "low side produces; high side ingests with a record", ""),
    ("ingest records", "high side", "the chain of custody for everything that crossed"),
    ("high-side changes", "high side", "divergence is recorded where it originates"),
    ("reconciliation obligations", PRODUCING_SIDE, ""),
    ("generated system truth", "each side for its own tree", ""),
    ("evidence export", "high side", "the deliverable record set for anything assessed against the high-side system (REQ-10.1.5)"),
]

# REQ-10.2.1–10.2.3: what crosses, in each direction. Nothing crosses that is not listed here.
CROSSINGS = {
    "low->high": [
        ("source", "source at a defined revision, with its file hashes"),
        ("gate-records", "the gate records covering a source drop, where the boundary permits"),
        ("catalogues", "vendored catalogues (§3.5)"),
        ("detection-data", "detection-data bundles (§4.2.2)"),
        ("scanner-images", "scanner image bundles (§4.1.1)"),
        ("approved-dependencies", "approved dependencies (§10.6)"),
    ],
    "high->low": [
        ("backport-patch", "a high-side change offered for back-port — a convenience where the boundary permits it; nothing here requires it"),
    ],
}
BACKPORT = ("not yet ported", "ported at revision ", "will not be ported: ")


class TopologyError(Exception):
    pass


def direction(from_side, to_side):
    return f"{from_side}->{to_side}"


def permitted(kind, from_side, to_side):
    return any(k == kind for k, _ in CROSSINGS.get(direction(from_side, to_side), []))


def render_authority(cfg):
    L = ["# Record authority (spec 04 §10.1)", "", f"this instance: side '{cfg.side}', topology '{cfg.topology}'", "",
         "Default: the side where the work happened owns the record. Records are never merged silently across the boundary; "
         "rows from the other side are retained and carry its side identifier. The high side's record set is the deliverable "
         "one for anything assessed against the high-side system.", "",
         "| artifact class | authoritative side | note |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in AUTHORITY]
    L += ["", "## What crosses", ""]
    for d, items in CROSSINGS.items():
        L.append(f"- {d}: " + "; ".join(f"{k} ({desc})" for k, desc in items))
    L.append("- nothing crosses that is not listed; no requirement depends on the high->low path")
    return "\n".join(L) + "\n"


# --- source drops, low to high (REQ-10.2.2, 10.2.4, 10.3.2) ---

def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def source_drop(root, out_dir, cfg, operator, revision="HEAD", include_records=True):
    """Package source at a defined revision with provenance and, where the boundary permits,
    the gate records covering it. Returns the manifest."""
    root = pathlib.Path(root)
    if cfg.side != "low":
        raise TopologyError(f"a source drop is produced on the low side; this instance is side '{cfg.side}'")
    if not operator.strip():
        raise TopologyError("every crossing names the operator responsible")
    rev = gitutil.rev(root, revision)
    if not rev:
        raise TopologyError(f"{revision} does not resolve to a commit")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tar = out / "source.tar"
    res = gitutil.git(root, "archive", "--format=tar", "-o", str(tar), rev)
    if res.returncode != 0:
        raise TopologyError(f"git archive failed: {res.stderr.strip()}")
    files = {}
    for f in gitutil.tracked_files(root):
        if f.startswith(".engine/records/") or f.startswith(".engine/work/"):
            continue
        show = gitutil.git(root, "show", f"{rev}:{f}")
        if show.returncode == 0:
            files[f] = _sha256(show.stdout.encode("utf-8", errors="replace"))
    data = {"kind": "source", "revision": rev, "tree": gitutil.git(root, "rev-parse", f"{rev}^{{tree}}").stdout.strip(),
            "produced": datetime.date.today().isoformat(), "source_side": cfg.side, "operator": operator.strip(),
            "files": files, "archive_sha256": _sha256(tar.read_bytes()), "records_transferred": bool(include_records)}
    if include_records:
        rec = out / "records"
        rec.mkdir(exist_ok=True)
        for p in gatelog.series_files(root):
            (rec / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        data["assessed"] = probes.assessed_files(root, cfg)
        data["records_sha256"] = {p.name: _sha256(p.read_bytes()) for p in sorted(rec.glob("*.md"))}
    data["bundle_id"] = f"source-{data['produced']}-{rev[:12]}"
    (out / "manifest.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def verify_drop(drop_dir):
    d = pathlib.Path(drop_dir)
    m = d / "manifest.json"
    if not m.is_file():
        raise TopologyError("drop carries no manifest.json")
    data = json.loads(m.read_text(encoding="utf-8"))
    for key in ("kind", "source_side", "produced", "operator", "bundle_id"):
        if not data.get(key):
            raise TopologyError(f"drop provenance lacks {key}")
    problems = []
    tar = d / "source.tar"
    if not tar.is_file():
        problems.append("source.tar absent")
    elif _sha256(tar.read_bytes()) != data.get("archive_sha256"):
        problems.append("source.tar: content hash differs from the manifest")
    for name, h in (data.get("records_sha256") or {}).items():
        p = d / "records" / name
        if not p.is_file():
            problems.append(f"records/{name} absent")
        elif _sha256(p.read_bytes()) != h:
            problems.append(f"records/{name}: content hash differs from the manifest")
    return data, problems


def receive_drop(root, drop_dir, cfg, operator, filtered_understood=""):
    """Receive a source drop on the high side: verify, refuse what is not enumerated, extract,
    import the transferred gate records as rows that keep their side, record the drop for the
    coverage inventory, and write the ingest record. Returns the manifest."""
    root = pathlib.Path(root)
    if not operator.strip():
        raise TopologyError("every crossing names the operator responsible")
    data, problems = verify_drop(drop_dir)
    if not permitted(data["kind"], data["source_side"], cfg.side):
        _ingest(root, cfg, data, "refused", "n/a", operator)
        raise TopologyError(f"'{data['kind']}' is not enumerated to cross {direction(data['source_side'], cfg.side)}; nothing crosses that is not enumerated")
    if problems:
        detail = "; ".join(problems)
        if not filtered_understood.strip():
            _ingest(root, cfg, data, f"MISMATCH ({detail})", "unknown — refused", operator)
            raise TopologyError("hash mismatch — drop refused. Either the boundary filtered the content (routine: re-request, or receive "
                                "with the filtering understood and recorded) or the drop is wrong (an integrity incident). " + detail)
        _ingest(root, cfg, data, f"MISMATCH ({detail})", f"yes — understood: {filtered_understood.strip()}", operator)
    else:
        _ingest(root, cfg, data, "verified", "no", operator)
    d = pathlib.Path(drop_dir)
    with tarfile.open(d / "source.tar") as tf:
        members = [m for m in tf.getmembers() if not m.name.startswith(".engine/records/") and not m.name.startswith(".engine/work/")]
        tf.extractall(root, members=members, filter="data")
    imported = 0
    if data.get("records_transferred"):
        imported = import_gate_records(root, cfg, d / "records")
    entry = {"bundle_id": data["bundle_id"], "revision": data["revision"], "source_side": data["source_side"], "produced": data["produced"],
             "received": datetime.date.today().isoformat(), "operator": operator.strip(), "files": sorted(data["files"]),
             "hashes": data["files"], "records_transferred": bool(data.get("records_transferred")),
             "assessed": data.get("assessed", {}) if data.get("records_transferred") else {}, "gate_rows_imported": imported}
    p = root / RECEIVED
    p.parent.mkdir(parents=True, exist_ok=True)
    drops = probes.received_drops(root)
    drops.append(entry)
    p.write_text(json.dumps({"drops": drops}, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def import_gate_records(root, cfg, records_dir):
    """Append the other side's gate rows to this side's series, keeping their side identifier.
    Rows claiming this side are refused: they would be indistinguishable (REQ-10.1.3)."""
    n = 0
    for p in sorted(pathlib.Path(records_dir).glob("gate-log*.md")):
        rows, probs, _ = table.parse(p.read_text(encoding="utf-8"), "gate-log")
        if probs:
            raise TopologyError(f"{p.name}: {probs[0]}")
        existing, _ = gatelog.series(root)
        have = {(r["side"], r["unit"], r["run"]) for r in existing}
        for r in rows:
            if r["side"] == cfg.side:
                raise TopologyError(f"transferred row {r['unit']}#{r['run']} claims side '{cfg.side}' — this side; rows are never merged without a distinguishable side")
            if (r["side"], r["unit"], r["run"]) in have:
                continue
            values = {c: r[c] for c in sch.GATE_LOG[2]}
            table.append(root, gatelog.FILE, sch.GATE_LOG, values)
            n += 1
    return n


def _ingest(root, cfg, data, hash_result, modified, operator):
    if not (pathlib.Path(root) / INGEST_RECORD).is_file():
        return
    table.append(root, INGEST_RECORD, sch.INGEST, {
        "date": now(cfg), "bundle": data.get("bundle_id", "?"), "production_date": data.get("produced", "?"),
        "arrival_date": datetime.date.today().isoformat(), "hash_result": hash_result, "modified_in_transit": modified,
        "operator": operator.strip(), "side": cfg.side})


# --- divergence: high-side-originated changes (REQ-10.4) ---

def backport_problem(status):
    s = status.strip()
    if s == BACKPORT[0]:
        return None
    if s.startswith(BACKPORT[1]) and len(s) > len(BACKPORT[1]):
        return None
    if s.startswith(BACKPORT[2]) and len(s.split(":", 1)[1].strip()) >= 10:
        return None
    if s.startswith("will not be ported"):
        return "'will not be ported' requires a written reason after the colon"
    return f"back-port status must be one of: {BACKPORT[0]!r}, 'ported at revision R', 'will not be ported: <reason>'"


def record_change(root, cfg, *, commit, what, why_not_low_side, authorized_by, backport_status):
    if cfg.side != "high":
        raise TopologyError(f"a high-side change is recorded on the high side; this instance is side '{cfg.side}'")
    for k, v in (("what", what), ("why_not_low_side", why_not_low_side), ("authorized_by", authorized_by)):
        if not str(v).strip():
            raise TopologyError(f"a high-side change record names {k}")
    p = backport_problem(backport_status)
    if p:
        raise TopologyError(p)
    full = gitutil.rev(root, commit)
    if not full:
        raise TopologyError(f"{commit} does not resolve to a commit on this side")
    return table.append(root, DIVERGENCE, sch.DIVERGENCE, {
        "date": now(cfg), "commit": full[:12], "what": what.strip(), "why_not_low_side": why_not_low_side.strip(),
        "authorized_by": authorized_by.strip(), "backport_status": backport_status.strip(), "side": cfg.side})


def changes(root):
    """Latest status per recorded high-side change."""
    rows, probs, _ = table.read(root, DIVERGENCE, "high-side-changes")
    latest = {}
    for r in rows or []:
        latest[r["commit"]] = r
    return list(latest.values()), probs


def unported(root):
    rows, _ = changes(root)
    return [r for r in rows if not r["backport_status"].startswith(BACKPORT[1])]


def received_content(root):
    """{path: sha256} of every file that arrived in a received drop."""
    out = {}
    for d in probes.received_drops(root):
        out.update(d.get("hashes", {}))
    return out


def originated_here(root, cfg, base, head):
    """Commits in the range that change content no received drop delivered: on the high side,
    these are high-side-originated changes and each needs a record (REQ-10.4.1)."""
    received = received_content(root)
    out = []
    for c in gitutil.commits_in(root, base, head):
        res = gitutil.git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", c)
        files = [f for f in res.stdout.splitlines() if f.strip() and not f.startswith(".engine/")]
        foreign = False
        for f in files:
            show = gitutil.git(root, "show", f"{c}:{f}")
            h = _sha256(show.stdout.encode("utf-8", errors="replace")) if show.returncode == 0 else None
            if received.get(f) != h:
                foreign = True
                break
        if files and foreign:
            out.append(c)
    return out


def ungated_changes(root, cfg):
    """Recorded high-side changes with no passing gate row whose range contains them (REQ-10.4.4)."""
    rows, _ = gatelog.series(root)
    covered = set()
    for r in rows:
        if r["verdict"] not in ("pass", "advisory") or r["_superseded"]:
            continue
        base, _, head = r["range"].partition("..")
        if gitutil.rev(root, base) and gitutil.rev(root, head):
            covered.update(c[:12] for c in gitutil.commits_in(root, base, head))
    rows, _ = changes(root)
    return [r for r in rows if r["commit"][:12] not in covered]


def report(root, cfg):
    """Lines for every gate and the export (REQ-10.4.3)."""
    if cfg.topology == "single":
        return [f"topology: single instance; no domain boundary"]
    un = unported(root)
    lines = [f"high-side changes unported: {len(un)}" + (f" ({', '.join(r['commit'] for r in un)})" if un else "")]
    return lines
