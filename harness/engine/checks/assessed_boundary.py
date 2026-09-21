# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The assessed boundary (spec 01 §9.3; spec 02 §8; spec 06 REQ-7.3; spec 02
REQ-4.4.1). Regenerates the coverage inventory, reports the never-assessed and
evidence-not-available proportions, requires a disposition for every adoption
inventory row, and reports inbound code that reached the protected branch
without a gate and without a recorded acceptance. Gates nothing on its own."""
import pathlib

from .. import gitutil, probes
from ..outcome import Outcome

NAME = "assessed-boundary"


def run(root, cfg):
    if not gitutil.is_repo(root):
        return Outcome.could_not_run(NAME, "not a git repository")
    rows, counts = probes.write_inventory(root, cfg)
    total = sum(counts.values())
    if total == 0:
        return Outcome.nothing_yet(NAME, "source files", "no tracked source files to classify")
    findings = []
    adoption = probes.adoption_problems(root)
    if adoption is not None:
        probs, n = adoption
        findings += [f"adoption inventory: {p}" for p in probs]
    ungated = probes.ungated_inbound(root, cfg)
    if ungated:
        findings += [f"ungated inbound: commit {c[:12]} reached the protected branch through no gate and no findings-register row records the acceptance"
                     for c in ungated[:20]]
    detail = (f"{counts['assessed']} assessed (at least once; not a clean bill of health), {counts['never']} never assessed, "
              f"{counts['elsewhere']} assessed elsewhere with evidence not available, of {total} source files — {probes.INVENTORY}")
    if findings:
        return Outcome.found(NAME, detail, findings, blocking=False)
    return Outcome.clean(NAME, detail)
