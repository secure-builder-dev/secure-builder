# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Reference integrity (spec 01 REQ-10.1; spec 02 REQ-11.4.1, REQ-4.1.5).

Every path cited in the governed document set must resolve. The governed set
is explicitly enumerated in the configuration (`governed_documents`, a list of
paths or globs), never inferred (spec 01 REQ-8.3.2). An empty set is a failed
check, not a vacuous pass (spec 03 REQ-1.4.2). A record whose pointers rot
reads as assurance while asserting nothing.
"""
import pathlib
import re

from ..outcome import Outcome

NAME = "reference-integrity"
DEFAULT_GOVERNED = ["AGENTS.md", ".engine/rules/RULES.md", ".engine/rules/agents/*.md", ".engine/rules/reference/*.md", ".engine/records/*.md"]
# a backtick-quoted token that looks like a repository path: has a slash or a file extension
PATH_TOKEN = re.compile(r"`([A-Za-z0-9_./-]+(?:/[A-Za-z0-9_.*-]+)+|[A-Za-z0-9_.-]+\.(?:md|json|py|js|ts|yml|yaml|toml|tsv|txt|sh))`")
NOT_A_PATH = re.compile(r"^(https?:|[A-Za-z]:)|^\.\.?$|^[0-9.]+$")


def governed_documents(root, cfg):
    patterns = (cfg.get("governed_documents") if cfg else None) or DEFAULT_GOVERNED
    root = pathlib.Path(root)
    out = []
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            out += [p for p in sorted(root.glob(pat)) if p.is_file()]
        elif (root / pat).is_file():
            out.append(root / pat)
    return out


def citations(text):
    seen = []
    for m in PATH_TOKEN.finditer(text):
        tok = m.group(1)
        if NOT_A_PATH.search(tok) or tok in seen:
            continue
        seen.append(tok)
    return seen


def resolves(root, tok, doc=None):
    """A citation resolves from the repository root, or from the citing document's directory."""
    root = pathlib.Path(root)
    bases = [root] + ([pathlib.Path(doc).parent] if doc else [])
    for base in bases:
        if any(ch in tok for ch in "*?["):
            if any(True for _ in base.glob(tok)):
                return True
        elif (base / tok).exists():
            return True
    return False


def run(root, cfg):
    docs = governed_documents(root, cfg)
    if not docs:
        return Outcome.could_not_run(NAME, "the governed document set resolved to zero documents — nothing to check is not a pass")
    findings, cited = [], 0
    for doc in docs:
        text = doc.read_text(encoding="utf-8", errors="replace")
        for tok in citations(text):
            cited += 1
            if not resolves(root, tok, doc):
                findings.append(f"{doc.relative_to(root).as_posix()}: `{tok}` does not resolve")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} of {cited} cited paths in {len(docs)} governed documents do not resolve",
                             findings, blocking=True)
    return Outcome.clean(NAME, f"{cited} cited paths in {len(docs)} governed documents all resolve")
