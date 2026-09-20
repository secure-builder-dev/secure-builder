# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Every registered check has a negative fixture (spec 05 REQ-2.1, REQ-2.3;
spec 01 REQ-13.4.1). A check whose fixture is missing is an untested check,
and this fails — so a check cannot be committed without the input that makes
it fail. Runs only where the self-test suite lives (the harness tree or a
placed copy); elsewhere it says so."""
import pathlib

from .. import audit
from ..outcome import Outcome

NAME = "negative-fixtures"


def run(root, cfg):
    from . import REGISTRY
    root = pathlib.Path(root)
    for cand in (root / ".engine" / "harness", root):
        if (cand / "engine" / "checks" / "__init__.py").is_file() and (cand / "selftest").is_dir():
            root = cand
            break
    else:
        return Outcome.could_not_run(NAME, "no harness self-test suite found beside the checks")
    if not REGISTRY:
        return Outcome.could_not_run(NAME, "the check registry is empty")
    missing = audit.q2_checks_without_negative_fixture(root, REGISTRY)
    if missing:
        return Outcome.found(NAME, "a check exists that has never been observed failing", missing, blocking=True)
    return Outcome.clean(NAME, f"all {len(REGISTRY)} registered checks have a self-test that makes them fail")
