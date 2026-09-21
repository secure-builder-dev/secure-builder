# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""License policy (spec 01 REQ-10.1, REQ-10.5; spec 06 REQ-8.4a). The generated
component record is compared against a declared policy. A record nothing
evaluates is an inventory; an undeclared policy cannot be evaluated against."""
from .. import licenses
from ..outcome import Outcome

NAME = "license-policy"


def run(root, cfg):
    rows = licenses.write_record(root)
    if not rows:
        return Outcome.nothing_yet(NAME, "third-party components", "no dependency manifest or lockfile is present")
    policy = licenses.read_policy(root)
    if policy is None:
        return Outcome.could_not_run(NAME, f"{len(rows)} components recorded but no license policy is declared at {licenses.POLICY}")
    findings = licenses.evaluate(rows, policy)
    if findings:
        return Outcome.found(NAME, f"{len(findings)} of {len(rows)} components fall outside the declared policy",
                             findings, blocking=True)
    return Outcome.clean(NAME, f"{len(rows)} components all within the declared policy ({len(policy['allowed'])} allowed licenses)")
