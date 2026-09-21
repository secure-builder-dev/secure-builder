# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Append-only markdown tables: the storage every record uses.

Plain text under version control, readable without the harness (spec 02
REQ-1.4). Rows are appended; nothing here rewrites or deletes a row. A file is
parsed against the schema its `Schema:` marker names; a schema boundary inside
a file is marked by a new `Schema:` line, so earlier rows are never left in an
old shape unmarked. A malformed row is reported, not skipped (REQ-11.2.2). A
file with a header and no rows is a template, distinguishable from a populated
record (REQ-11.3.1).
"""
import pathlib
import re

from . import schema as sch

MARKER = re.compile(r"^Schema:\s*([\w-]+)/(\d+)\.?", re.M)
PLACEHOLDER = re.compile(r"<[^>]+>|\bTODO\b|\bTBD\b|\bexample\b", re.I)


class Malformed(Exception):
    pass


def _cell(v):
    return str(v).replace("|", "\\|").replace("\n", " ").strip()


def _split(line):
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|")) if line.strip().startswith("|") else None
    return [p.replace("\\|", "|").strip() for p in parts] if parts is not None else None


def parse(text, schema_name):
    """Rows for one schema in a file. Returns (rows, problems, versions_seen).
    Each row is a dict plus '_line' (1-based) and '_version'."""
    rows, problems, versions = [], [], []
    current = None          # (name, version, columns) while inside a matching table
    header_seen = False
    for n, line in enumerate(text.splitlines(), 1):
        m = MARKER.match(line)
        if m:
            name, version = m.group(1), int(m.group(2))
            if name == schema_name:
                known = sch.ALL.get(name)
                if known and known[1] == version:
                    current = known
                    versions.append(version)
                else:
                    problems.append(f"line {n}: schema {name}/{version} is not a version this harness knows")
                    current = None
                header_seen = False
            else:
                current = None
            continue
        if current is None:
            continue
        cells = _split(line)
        if cells is None:
            continue
        if not header_seen:
            if cells != current[2]:
                problems.append(f"line {n}: header {cells} does not match schema {current[0]}/{current[1]} {current[2]}")
                current = None
                continue
            header_seen = True
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        if len(cells) != len(current[2]):
            problems.append(f"line {n}: row has {len(cells)} cells, schema {current[0]}/{current[1]} has {len(current[2])}")
            continue
        row = dict(zip(current[2], cells))
        row["_line"] = n
        row["_version"] = current[1]
        rows.append(row)
    return rows, problems, versions


def read(root, rel, schema_name):
    p = pathlib.Path(root) / rel
    if not p.is_file():
        return None, [f"{rel} does not exist"], []
    return parse(p.read_text(encoding="utf-8"), schema_name)


def is_template_only(rows):
    """A record with no real rows, or only placeholder rows, is a template."""
    if not rows:
        return True
    for r in rows:
        values = " ".join(v for k, v in r.items() if not k.startswith("_"))
        if not PLACEHOLDER.search(values):
            return False
    return True


def append(root, rel, schema, values):
    """Append one row under the schema's table. Every column is required; a value the
    writer does not know is written as 'unknown', never left empty (spec 02 REQ-3.1.8)."""
    name, version, columns = schema
    missing = [c for c in columns if c not in values]
    if missing:
        raise Malformed(f"{name}: missing columns {missing}")
    extra = [k for k in values if k not in columns]
    if extra:
        raise Malformed(f"{name}: unknown columns {extra}")
    p = pathlib.Path(root) / rel
    if not p.is_file():
        raise Malformed(f"{rel} does not exist; records are seeded, never created by a writer")
    text = p.read_text(encoding="utf-8")
    line = "| " + " | ".join(_cell(values[c]) if str(values[c]).strip() else sch.UNKNOWN for c in columns) + " |"
    # insert after the last row of this schema's most recent table
    lines = text.splitlines()
    idx = _last_row_index(lines, name)
    if idx is None:
        raise Malformed(f"{rel} carries no table for schema {name}/{version}")
    lines.insert(idx + 1, line)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return line


def _last_row_index(lines, schema_name):
    inside, last = False, None
    for i, line in enumerate(lines):
        m = MARKER.match(line)
        if m:
            inside = m.group(1) == schema_name
            continue
        if inside and line.strip().startswith("|"):
            last = i
        elif inside and last is not None and line.strip() and not line.strip().startswith("|"):
            inside = False
    return last


def rows_text(lines_or_text):
    """The row lines only (used by the integrity check)."""
    text = lines_or_text if isinstance(lines_or_text, str) else "\n".join(lines_or_text)
    return [l for l in text.splitlines() if l.strip().startswith("|")
            and not all(re.fullmatch(r":?-+:?", c) for c in _split(l) or ["x"])]
