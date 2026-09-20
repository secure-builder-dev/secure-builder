# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Reviewer-document consistency (spec 01 REQ-6.5.2; spec 03 REQ-1.4.1–1.4.2).

Wherever a format is defined in one place and written in another, the copies
must agree. A duplicated block is delimited in a document by
`<!-- engine:block NAME -->` ... `<!-- engine:end NAME -->`. The project declares
the names it expects to be duplicated (`consistency_blocks` in the
configuration); every declared name must occur at least twice across the
governed set, byte-identical. A declared block found once or not at all is a
finding — the check follows the reference chain from the instruction file and
fails rather than passing when the thing it was told to compare is absent.
"""
import pathlib
import re

from ..outcome import Outcome
from .reference_integrity import governed_documents

NAME = "doc-consistency"
BLOCK = re.compile(r"<!--\s*engine:block\s+([\w.-]+)\s*-->\n?(.*?)<!--\s*engine:end\s+\1\s*-->", re.S)
REFERENCE = re.compile(r"^Read and follow:\s*(\S+)\s*$", re.M)


def document_set(root, cfg):
    """Governed documents plus anything the instruction file references (one level)."""
    root = pathlib.Path(root)
    docs = list(governed_documents(root, cfg))
    for doc in list(docs):
        for m in REFERENCE.finditer(doc.read_text(encoding="utf-8", errors="replace")):
            p = root / m.group(1)
            if p.is_file() and p not in docs:
                docs.append(p)
    return docs


def blocks(docs, root):
    found = {}
    for doc in docs:
        for m in BLOCK.finditer(doc.read_text(encoding="utf-8", errors="replace")):
            found.setdefault(m.group(1), []).append((pathlib.Path(doc).relative_to(root).as_posix(), m.group(2).strip()))
    return found


def run(root, cfg):
    declared = list((cfg.get("consistency_blocks") if cfg else None) or [])
    if not declared:
        return Outcome.nothing_yet(NAME, "declared duplicated formats",
                                   "the project declares no format that is written in more than one place (consistency_blocks)")
    docs = document_set(root, cfg)
    if not docs:
        return Outcome.could_not_run(NAME, "the governed document set resolved to zero documents")
    found = blocks(docs, pathlib.Path(root))
    findings = []
    for name in declared:
        copies = found.get(name, [])
        if len(copies) < 2:
            where = ", ".join(c[0] for c in copies) or "nowhere"
            findings.append(f"block '{name}': expected in at least two documents, found in {len(copies)} ({where}) — nothing to compare")
            continue
        distinct = {c[1] for c in copies}
        if len(distinct) > 1:
            findings.append(f"block '{name}': {len(copies)} copies disagree ({', '.join(c[0] for c in copies)})")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} declared format(s) inconsistent or missing", findings, blocking=True)
    return Outcome.clean(NAME, f"{len(declared)} declared format(s) identical across every copy in {len(docs)} documents")
