# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""High-side divergence (spec 04 §10.4): the count of unported high-side changes is
reported at every gate; a recorded high-side change that no high-side gate has passed
is blocking — urgency skips the transfer window, never the review."""
import pathlib

from .. import topology
from ..outcome import Outcome

NAME = "high-side-changes"


def run(root, cfg):
    if cfg is None:
        return Outcome.could_not_run(NAME, "no configuration")
    if cfg.topology == "single":
        return Outcome.not_applicable(NAME, "single-instance topology", "no domain boundary, so no side can diverge from another",
                                      "the gate log of the one instance")
    if not (pathlib.Path(root) / topology.DIVERGENCE).is_file():
        return Outcome.could_not_run(NAME, f"{topology.DIVERGENCE} is absent; a two-instance topology keeps this record")
    rows, probs = topology.changes(root)
    if probs:
        return Outcome.could_not_run(NAME, f"{topology.DIVERGENCE}: {probs[0]}")
    findings = []
    bad = [r for r in rows if topology.backport_problem(r["backport_status"])]
    findings += [f"{r['commit']}: {topology.backport_problem(r['backport_status'])}" for r in bad]
    for r in topology.ungated_changes(root, cfg):
        findings.append(f"{r['commit']} ({r['what']}): recorded as a high-side change but no high-side gate row covers it — "
                        "urgency skips the transfer window, not the review")
    detail = topology.report(root, cfg)[0]
    if findings:
        return Outcome.found(NAME, detail, findings, blocking=True)
    if not rows:
        return Outcome.nothing_yet(NAME, "high-side-originated change", detail)
    return Outcome.clean(NAME, detail)
