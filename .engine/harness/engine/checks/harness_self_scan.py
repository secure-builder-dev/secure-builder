# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Harness self-scan (spec 01 REQ-10.6). The harness is subject to the scan
policy it applies to projects: its own source carries no credential-shaped
content, it imports nothing outside the standard library (so it has no
third-party components to license or to carry vulnerabilities), and any
vendored data it carries verifies against its recorded provenance hash."""
import ast
import hashlib
import json
import pathlib
import sys

from ..outcome import Outcome
from .credential_scan import scan_text
from .no_network import harness_tree

NAME = "harness-self-scan"
CATALOGUES = ".engine/rules/catalogues"


def imports_of(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def third_party_imports(here):
    stdlib = set(sys.stdlib_module_names) | {"engine", "selftest", "integration"}
    out = []
    for p in sorted(here.rglob("*.py")):
        for name in sorted(imports_of(p) - stdlib):
            out.append(f"{p.relative_to(here.parent).as_posix()}: imports third-party module '{name}'")
    return out


def catalogue_problems(root):
    """Vendored catalogues must verify against the hash their provenance records."""
    d = pathlib.Path(root) / CATALOGUES
    out = []
    if not d.is_dir():
        return out
    for prov in sorted(d.glob("*.provenance.json")):
        try:
            meta = json.loads(prov.read_text(encoding="utf-8"))
            data = d / meta["file"]
            digest = hashlib.sha256(data.read_bytes()).hexdigest()
            if digest != meta["sha256"]:
                out.append(f"{data.name}: content hash differs from its recorded provenance")
        except (ValueError, KeyError, OSError) as e:
            out.append(f"{prov.name}: provenance unreadable ({type(e).__name__})")
    return out


def run(root, cfg):
    here = harness_tree(root)
    if here is None:
        return Outcome.could_not_run(NAME, "no harness source tree found under the project root")
    findings = third_party_imports(here)
    scanned = 0
    for p in sorted(here.rglob("*.py")):
        scanned += 1
        findings += [f"harness {f}" for f in scan_text(p.relative_to(here.parent).as_posix(), p.read_text(encoding="utf-8", errors="replace"))]
    findings += catalogue_problems(root)
    if scanned == 0:
        return Outcome.could_not_run(NAME, "harness tree holds no source files")
    if findings:
        return Outcome.found(NAME, "the harness fails the policy it applies to projects", findings, blocking=True)
    return Outcome.clean(NAME, f"{scanned} harness modules: standard library only, no credential-shaped content, vendored data verifies")
