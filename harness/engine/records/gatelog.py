# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The gate log (spec 02 §3; spec 01 §12). The primary assessment record.

One row per gate run, including every re-run; re-runs append, never replace.
The range is commit identifiers. Finding identifiers are recorded, not only
counts. Every row records the reviewer class, the human who attests, the
harness version and the checklist version — or the word 'unknown', never an
empty cell. A field verdict is a row of a distinct class in the same series
(spec 11 REQ-6.3). A wrong verdict is superseded by a later row that says so;
it is never erased (REQ-11.5).

Started markers (§3.5) are written by the handoff generator before a gate runs,
into a directory the gate does not write; a marker with no completed row is a
checkable gap, and the marker is never deleted in normal operation.

Storage: `.engine/records/gate-log.md`, plus rotated files
`gate-log.<period>.md` and, for teams past the single-writer assumption, one
file per run under `gate-log/`. `series()` reads all of them as one artifact
(REQ-2.4.4, REQ-2.6.1).
"""
import json
import pathlib
import re

from . import now, records_dir, table
from . import schema as sch

FILE = ".engine/records/gate-log.md"
PER_RUN_DIR = ".engine/records/gate-log"
STARTED_DIR = ".engine/records/started"
ROTATED = re.compile(r"^gate-log\.(\d{4}(?:-\d{2})?)\.md$")


def series_files(root):
    d = records_dir(root)
    out = []
    if (d / "gate-log.md").is_file():
        out.append(d / "gate-log.md")
    out += sorted(p for p in d.glob("gate-log.*.md") if ROTATED.match(p.name))
    if (d / "gate-log").is_dir():
        out += sorted((d / "gate-log").glob("*.md"))
    return out


def series(root):
    """Every row in the series, in file order, with superseded rows marked."""
    rows, problems = [], []
    for p in series_files(root):
        r, pr, _ = table.parse(p.read_text(encoding="utf-8"), "gate-log")
        for row in r:
            row["_file"] = p.relative_to(root).as_posix()
        rows += r
        problems += [f"{p.name}: {x}" for x in pr]
    superseded = {row["supersedes"] for row in rows if row.get("supersedes") not in ("", "-", sch.UNKNOWN)}
    for row in rows:
        row["_superseded"] = f"{row['unit']}#{row['run']}" in superseded
    return rows, problems


def append(root, cfg, **fields):
    """Append a gate-log row. Required: unit, range, run, verdict, reviewer,
    reviewer_class, attested_by. Everything else defaults to 'unknown' or '-'."""
    for key in ("unit", "range", "run", "verdict", "reviewer", "reviewer_class", "attested_by"):
        if not str(fields.get(key, "")).strip():
            raise table.Malformed(f"gate-log row requires {key}")
    if fields["reviewer_class"] not in sch.REVIEWER_CLASSES:
        raise table.Malformed(f"reviewer_class must be one of {sch.REVIEWER_CLASSES}")
    if fields["verdict"] not in sch.VERDICTS:
        raise table.Malformed(f"verdict must be one of {sch.VERDICTS}")
    if not re.fullmatch(r"[0-9a-f]{7,40}\.\.[0-9a-f]{7,40}", str(fields["range"])):
        raise table.Malformed("range must be commit identifiers base..head, never branch names")
    f = str(fields.get("findings", "0")).strip()
    if not re.fullmatch(r"0|\d+: *\S.*", f):
        raise table.Malformed("findings records identifiers, not only a count: '0' or 'N: F-1, F-2, ...'")
    values = {c: sch.UNKNOWN for c in sch.GATE_LOG[2]}
    values.update({"date": now(cfg), "mode": "normal", "findings": "0", "tickets": "-", "controls": "-",
                   "supersedes": "-", "deferred": "-", "obligation": "-", "side": cfg.side if cfg else sch.UNKNOWN,
                   "model": "-"})
    values.update({k: v for k, v in fields.items() if k in values})
    if values["mode"] not in sch.MODES:
        raise table.Malformed(f"mode must be one of {sch.MODES}")
    if values["mode"] == "field" and not values["verdict"].startswith("field-"):
        raise table.Malformed("a field-mode row carries a field-pass/field-fail verdict, never an ordinary pass")
    if values["mode"] == "normal" and values["verdict"].startswith("field-"):
        raise table.Malformed("a field verdict belongs to a field-mode row")
    return table.append(root, FILE, sch.GATE_LOG, values)


def supersede(root, cfg, unit, run, what_was_wrong, how_found, disposition, attested_by, reviewer):
    """Append a superseding row for a verdict later found wrong (REQ-11.5). The
    original row remains; this row references it and records the disposition."""
    rows, _ = series(root)
    orig = [r for r in rows if r["unit"] == unit and r["run"] == str(run)]
    if not orig:
        raise table.Malformed(f"no row for {unit}#{run} to supersede")
    o = orig[-1]
    return append(root, cfg, unit=unit, range=o["range"], run=f"{run}s", verdict="superseded",
                  findings=f"1: superseding {unit}#{run} — wrong: {what_was_wrong}; found by: {how_found}; disposition: {disposition}",
                  reviewer=reviewer, reviewer_class="human", attested_by=attested_by,
                  harness_version=o.get("harness_version", sch.UNKNOWN), checklist_version=o.get("checklist_version", sch.UNKNOWN),
                  supersedes=f"{unit}#{run}")


# --- started markers (REQ-3.5) ---

def write_started(root, cfg, unit, run, range_, head, extra=None):
    d = pathlib.Path(root) / STARTED_DIR
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{unit}-{run}.json"
    if p.exists():
        raise table.Malformed(f"started marker {p.name} already exists; a run number is used once")
    data = {"unit": unit, "run": str(run), "range": range_, "head": head, "started": now(cfg),
            "side": cfg.side if cfg else sch.UNKNOWN}
    data.update(extra or {})
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return p


def started_markers(root):
    d = pathlib.Path(root) / STARTED_DIR
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            out.append({"unit": p.stem, "run": "?", "_malformed": True})
    return out


def unmatched_markers(root):
    """Started markers with no completed row (REQ-3.5.2)."""
    rows, _ = series(root)
    done = {(r["unit"], r["run"]) for r in rows}
    return [m for m in started_markers(root) if (m.get("unit"), m.get("run")) not in done]


# --- rotation (REQ-2.6) ---

def rotate(root, period_key):
    """Move rows whose date starts with period_key (e.g. '2025') into
    gate-log.<period>.md. Nothing is deleted; the series reads both."""
    d = records_dir(root)
    src = d / "gate-log.md"
    text = src.read_text(encoding="utf-8")
    rows, problems, _ = table.parse(text, "gate-log")
    moving = [r for r in rows if r["date"].startswith(period_key)]
    if not moving:
        return 0
    lines = text.splitlines()
    moved_lines = [lines[r["_line"] - 1] for r in moving]
    keep = [l for i, l in enumerate(lines, 1) if i not in {r["_line"] for r in moving}]
    dst = d / f"gate-log.{period_key}.md"
    if not dst.exists():
        dst.write_text(f"# Gate log — {period_key}\n\nRotated from gate-log.md. Part of one series.\n\n"
                       f"{sch.marker_line(sch.GATE_LOG)}\n\n{sch.header_line(sch.GATE_LOG)}\n{sch.separator_line(sch.GATE_LOG)}\n",
                       encoding="utf-8", newline="\n")
    with dst.open("a", encoding="utf-8", newline="\n") as f:
        for l in moved_lines:
            f.write(l + "\n")
    src.write_text("\n".join(keep) + "\n", encoding="utf-8", newline="\n")
    index = d / "README.md"
    note = f"- gate-log.{period_key}.md — rows dated {period_key}, rotated; read as part of the series\n"
    if index.is_file() and note not in index.read_text(encoding="utf-8"):
        with index.open("a", encoding="utf-8", newline="\n") as f:
            f.write(note)
    return len(moving)
