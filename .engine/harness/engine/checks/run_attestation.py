# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Run attestation (spec 02 §3.5). Every started marker has a completed
gate-log row; a marker without one is the visible, checkable gap that makes a
missing failing row detectable. Runs in the ordinary mechanical set."""
import pathlib

from ..outcome import Outcome
from ..records import gatelog

NAME = "run-attestation"


def run(root, cfg):
    root = pathlib.Path(root)
    if not (root / ".engine" / "records").is_dir():
        return Outcome.could_not_run(NAME, ".engine/records does not exist")
    markers = gatelog.started_markers(root)
    rows, problems = gatelog.series(root)
    if problems:
        return Outcome.could_not_run(NAME, "gate log unreadable: " + "; ".join(problems[:3]))
    if not markers and not rows:
        return Outcome.nothing_yet(NAME, "gate runs", "no gate has started and no row has been written")
    findings = [f"{m.get('unit')}#{m.get('run')}: started {m.get('started', '?')} on {m.get('range', '?')}, no completed row"
                for m in gatelog.unmatched_markers(root)]
    findings += [f"{m.get('unit')}: started marker is malformed" for m in markers if m.get("_malformed")]
    orphan_rows = [r for r in rows if not r["_superseded"] and r["verdict"] != "superseded"
                   and (r["unit"], r["run"]) not in {(m.get("unit"), m.get("run")) for m in markers}]
    findings += [f"{r['unit']}#{r['run']}: gate-log row has no started marker — a row written with no run behind it"
                 for r in orphan_rows]
    if findings:
        return Outcome.found(NAME, f"{len(findings)} gate run(s) cannot be attested", findings, blocking=True)
    return Outcome.clean(NAME, f"{len(markers)} started marker(s) each have a completed row, and every row has a marker")
