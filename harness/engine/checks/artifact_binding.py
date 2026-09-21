# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Artifact binding (spec 01 REQ-4.9.3–4.9.5). The digest the gate blessed —
recorded in the scan stamp for the reviewed commit — is the digest the
deployment pipeline ships. A mismatch is reported as *the artifact under
review is not the artifact being shipped*, never as a scan failure."""
import json
import pathlib

from .. import stamp
from ..outcome import Outcome

NAME = "artifact-binding"
DEFAULT_LOCK = "deploy/images.lock.json"


def shipped_digests(root, cfg):
    p = pathlib.Path(root) / ((cfg.get("shipped_digests") if cfg else None) or DEFAULT_LOCK)
    if not p.is_file():
        return None, p
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}, p
    return ({k: str(v) for k, v in data.items()} if isinstance(data, dict) else {}), p


def run(root, cfg):
    st = stamp.read(root)
    if st is None:
        return Outcome.nothing_yet(NAME, "scan stamp", "no scan has recorded an image digest yet")
    digests = st.get("digests") or {}
    shipped, lock = shipped_digests(root, cfg)
    if not digests and shipped is None:
        return Outcome.nothing_yet(NAME, "shipped images", "the scan built no images and no deployment lock names any")
    if shipped is None:
        return Outcome.could_not_run(NAME, f"the scan recorded {len(digests)} image digest(s) but {lock.relative_to(root).as_posix()} names none shipped")
    findings = []
    for name, digest in digests.items():
        ship = shipped.get(name)
        if ship is None:
            findings.append(f"{name}: scanned ({digest[:19]}…) but the deployment pipeline names no digest for it")
        elif ship != digest:
            findings.append(f"{name}: the artifact under review ({digest[:19]}…) is not the artifact being shipped ({ship[:19]}…)")
    for name in shipped:
        if name not in digests:
            findings.append(f"{name}: shipped by the pipeline but never scanned for commit {st.get('commit', '?')[:12]}")
    if findings:
        return Outcome.found(NAME, "the artifact under review is not the artifact being shipped", findings, blocking=True)
    return Outcome.clean(NAME, f"{len(digests)} image digest(s) blessed for {st.get('commit', '?')[:12]} match the pipeline's shipped digests")
