# © 2026 Casey Houle. All rights reserved.
"""engine — an assurance harness. See specs/ for what it must do and why."""
import hashlib
import pathlib

RELEASE = "0.1.0-dev"


def version():
    """Content-derived version identity (spec 06 REQ-5.2): a digest over every
    engine-owned source file, so the version cannot drift from what was copied."""
    here = pathlib.Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(here.rglob("*.py")):
        h.update(p.relative_to(here).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return f"{RELEASE}+{h.hexdigest()[:12]}"
