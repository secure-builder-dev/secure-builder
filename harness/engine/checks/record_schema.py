# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Record schema conformance (spec 02 REQ-3.3.2, REQ-11.2, REQ-11.3).

Every record file's table header matches the schema the writers emit; a
malformed row is treated as absent and reported; a record holding only
template placeholders is distinguishable from a populated one and is never
reported as success. Absent records are findings, not gaps (REQ-11.1.1)."""
import pathlib

from ..outcome import Outcome
from ..records import gatelog, table
from ..records import schema as sch

NAME = "record-schema"
# records whose absence leaves another check verifying nothing: their absence blocks
LOAD_BEARING = {".engine/records/gate-log.md", ".engine/records/findings-register.md"}


def run(root, cfg):
    root = pathlib.Path(root)
    if not (root / ".engine" / "records").is_dir():
        return Outcome.could_not_run(NAME, ".engine/records does not exist — the record set was never seeded")
    findings, populated, template_only, tickets = [], [], [], []
    for rel, schemas in sch.FILES.items():
        p = root / rel
        if not p.is_file():
            if rel in LOAD_BEARING:
                findings.append(f"{rel}: required record is absent — another check would verify nothing without it")
            else:
                tickets.append(f"{rel}: required record is absent — open a ticket to seed it (spec 02 REQ-11.1.2)")
            continue
        text = p.read_text(encoding="utf-8")
        for name in schemas:
            rows, problems, versions = table.parse(text, name)
            findings += [f"{rel} [{name}]: {x}" for x in problems]
            if not versions:
                findings.append(f"{rel}: carries no table for schema {name}/{sch.ALL[name][1]}")
                continue
            (template_only if table.is_template_only(rows) else populated).append(name)
    for p in gatelog.series_files(root):
        if p.name != "gate-log.md":
            _, problems, _ = table.parse(p.read_text(encoding="utf-8"), "gate-log")
            findings += [f"{p.relative_to(root).as_posix()}: {x}" for x in problems]
    if findings:
        return Outcome.found(NAME, f"{len(findings)} record schema problem(s)", findings + tickets, blocking=True)
    if tickets:
        return Outcome.found(NAME, f"{len(tickets)} record(s) absent — bookkeeping, not safety", tickets, blocking=False)
    if not populated:
        return Outcome.nothing_yet(NAME, "populated records",
                                   f"all {len(template_only)} record tables hold only their template — valid, and not evidence of anything")
    return Outcome.clean(NAME, f"{len(populated)} populated and {len(template_only)} template-only record tables conform to their schemas")
