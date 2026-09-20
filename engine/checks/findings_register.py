# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The findings register, read at gate start (spec 02 REQ-4.1.4, REQ-4.1.5,
REQ-4.2.2, REQ-4.2.3). A Table A row whose mechanism no longer resolves is a
blocking finding — the check itself has regressed. A Table B row whose proof is
unsatisfied is reported every run, without exception, until it is; one marked
accepted without proof blocks."""
import pathlib

from ..outcome import Outcome
from ..records import findings, table

NAME = "findings-register"


def run(root, cfg):
    root = pathlib.Path(root)
    if not (root / findings.FILE).is_file():
        return Outcome.could_not_run(NAME, f"{findings.FILE} does not exist")
    blocking, reported, parse_problems = findings.problems(root)
    if parse_problems:
        return Outcome.could_not_run(NAME, "register unreadable: " + "; ".join(parse_problems[:3]))
    a, b, _ = findings.read(root)
    if table.is_template_only(a) and table.is_template_only(b):
        return Outcome.nothing_yet(NAME, "findings", "the register holds no rows yet — nothing has been found, or nothing has been recorded")
    if blocking:
        return Outcome.found(NAME, f"{len(blocking)} blocking; {len(reported)} open risk(s) awaiting proof",
                             blocking + reported, blocking=True)
    if reported:
        return Outcome.found(NAME, f"{len(reported)} accepted-risk row(s) whose compensating control has no proof — reported every run",
                             reported, blocking=False)
    return Outcome.clean(NAME, f"{len(a)} permanent check(s) resolve; {len(b)} risk row(s) carry satisfied proof or are closed")
