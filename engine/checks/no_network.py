# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Harness self-scan: no component reaches the network except through engine/net.py
(spec 04 REQ-2.2; spec 01 §14). Reads the harness's own source tree."""
import pathlib
import re

from ..outcome import Outcome

FORBIDDEN = re.compile(r"^\s*(import|from)\s+(socket|urllib|http\.client|http\b|ssl|ftplib|smtplib|xmlrpc)")
NAME = "no-network"


def harness_tree(root):
    """The harness source under root: the engine itself, or a placed copy."""
    root = pathlib.Path(root)
    for cand in (root / "engine", root / ".engine" / "harness" / "engine"):
        if (cand / "checks" / "__init__.py").is_file():
            return cand
    return None


def run(root, cfg):
    here = harness_tree(root)
    if here is None:
        return Outcome.could_not_run(NAME, "no harness source tree found under the project root")
    hits = []
    scanned = 0
    for p in sorted(here.rglob("*.py")):
        if p.name == "net.py":
            continue
        scanned += 1
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN.match(line):
                hits.append(f"{p.relative_to(here.parent).as_posix()}:{n}: {line.strip()}")
    if scanned == 0:
        return Outcome.could_not_run(NAME, "found no harness source files to scan")
    if hits:
        return Outcome.found(NAME, "a component imports a network library directly", hits, blocking=True)
    return Outcome.clean(NAME, f"{scanned} harness modules import no network library outside net.py")
