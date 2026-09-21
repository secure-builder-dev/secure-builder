# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Record integrity (spec 02 REQ-10.3.1, REQ-3.5.4, REQ-2.4.2, §12).

Records are append-only by convention, and the convention is checked: every
row that was present in the last committed version of a record must still be
present, unchanged, in the working tree — a resolution that drops a row is a
record deletion. Started markers are never deleted in normal operation."""
import pathlib

from .. import gitutil
from ..outcome import Outcome
from ..records import gatelog, table
from ..records import schema as sch

NAME = "record-integrity"


def committed_text(root, rel):
    res = gitutil.git(root, "show", f"HEAD:{rel}")
    return res.stdout if res.returncode == 0 else None


def run(root, cfg):
    root = pathlib.Path(root)
    if not gitutil.is_repo(root) or not gitutil.head(root):
        return Outcome.could_not_run(NAME, "no committed history to compare records against")
    files = list(sch.FILES) + [p.relative_to(root).as_posix() for p in gatelog.series_files(root) if p.name != "gate-log.md"]
    findings, compared = [], 0
    for rel in files:
        before = committed_text(root, rel)
        if before is None:
            continue
        compared += 1
        p = root / rel
        if not p.is_file():
            findings.append(f"{rel}: committed record is missing from the working tree")
            continue
        old_rows = table.rows_text(before)
        new_rows = set(table.rows_text(p.read_text(encoding="utf-8")))
        for row in old_rows:
            if row not in new_rows:
                findings.append(f"{rel}: a previously committed row was altered or removed: {row[:80]}")
    # started markers: any deleted relative to HEAD is a record deletion
    res = gitutil.git(root, "diff", "--name-only", "--diff-filter=D", "HEAD", "--", gatelog.STARTED_DIR)
    for rel in [l for l in res.stdout.splitlines() if l.strip()]:
        findings.append(f"{rel}: started marker deleted — a marker is a record and is never removed")
    if compared == 0 and not findings:
        return Outcome.nothing_yet(NAME, "committed records", "no record file has been committed yet")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} record(s) altered, removed or deleted", findings, blocking=True)
    return Outcome.clean(NAME, f"{compared} committed record file(s): every prior row still present and unchanged")
