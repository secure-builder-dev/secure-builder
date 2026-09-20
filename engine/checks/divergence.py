# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Engine-owned divergence check (spec 06 REQ-5.4–5.5).

Reports whether the project's copy of every engine-owned file matches the
version the update recorded. This is what makes the overwrite guarantee real:
without it the guarantee holds only for projects that actually run the update.
Runs in the routine check command, not as a maintenance tool.
"""
import json
import pathlib

from .. import ownership as own
from ..distribute import sha
from ..outcome import Outcome

NAME = "engine-divergence"


def run(root, cfg):
    root = pathlib.Path(root)
    placed = root / own.PLACED_MANIFEST
    if not placed.is_file():
        if (root / "engine" / "ownership.py").is_file():
            return Outcome.not_applicable(
                NAME, "harness source tree", "no placed copy exists; this tree is the engine itself",
                "the content-derived version (engine.version()) is computed from source on every run")
        return Outcome.could_not_run(NAME, f"{own.PLACED_MANIFEST} is absent — the harness was never placed here")
    try:
        data = json.loads(placed.read_text(encoding="utf-8"))
        files = data["files"]
        recorded = data["version"]
    except (ValueError, KeyError, TypeError):
        return Outcome.could_not_run(NAME, f"{own.PLACED_MANIFEST} is unreadable")
    if not files:
        return Outcome.could_not_run(NAME, f"{own.PLACED_MANIFEST} lists no files — nothing to compare is not a pass")
    findings = []
    for rel, digest in sorted(files.items()):
        p = root / rel
        if not p.is_file():
            findings.append(f"{rel}: missing (placed by version {recorded})")
            continue
        if sha(p.read_bytes()) != digest:
            findings.append(f"{rel}: differs from the copy version {recorded} placed")
        elif own.marker_required(rel) and own.ENGINE_OWNED_MARKER not in p.read_text(encoding="utf-8", errors="replace"):
            findings.append(f"{rel}: engine-owned file carries no ENGINE-OWNED marker")
    version_file = root / own.VERSION_FILE
    if not version_file.is_file():
        findings.append(f"{own.VERSION_FILE}: missing — the project cannot state which harness version it carries")
    elif version_file.read_text(encoding="utf-8").splitlines()[:1] != [recorded]:
        findings.append(f"{own.VERSION_FILE} names a different version than {own.PLACED_MANIFEST}")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} engine-owned file(s) diverge from version {recorded}",
                             findings, blocking=True)
    return Outcome.clean(NAME, f"{len(files)} engine-owned files match version {recorded}")
