# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The scan verdict stamp (spec 01 §4.8, §4.9.3; spec 02 §6.2, REQ-2.3.1–2.3.2).

A completed scan writes a machine-readable stamp: the commit scanned, the
verdict, a timestamp, which scanners ran, and the digest of each image built
from that commit. The stamp is a record and is committed; it carries no
environment identifier. The handoff reads it, and a stamp naming a different
commit is no stamp at all.
"""
import json
import pathlib
import re

FILE = ".engine/records/scan/stamp.json"
VERDICTS = ("green", "red", "unverified")
FORBIDDEN_KEYS = ("host", "hostname", "registry", "account", "account_id", "url", "path", "workstation")


def write(root, *, commit, verdict, timestamp, scanners, digests=None, detection_data_date=None, mode=None):
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        raise ValueError("commit must be a commit identifier")
    data = {"commit": commit, "verdict": verdict, "timestamp": timestamp, "scanners": list(scanners),
            "digests": dict(digests or {})}
    if detection_data_date:
        data["detection_data_date"] = detection_data_date
    if mode:
        data["mode"] = mode
    p = pathlib.Path(root) / FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def read(root):
    p = pathlib.Path(root) / FILE
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def problems(data):
    out = []
    if not isinstance(data, dict):
        return ["stamp is not an object"]
    for k in ("commit", "verdict", "timestamp", "scanners"):
        if k not in data:
            out.append(f"stamp lacks '{k}'")
    if data.get("verdict") not in VERDICTS:
        out.append(f"stamp verdict {data.get('verdict')!r} is not one of {VERDICTS}")
    for k in FORBIDDEN_KEYS:
        if k in data:
            out.append(f"stamp carries an environment identifier ('{k}'); it must not")
    return out


def for_commit(root, commit):
    """The stamp if it describes exactly this commit and is well-formed, else None."""
    data = read(root)
    if data is None or problems(data):
        return None
    if data.get("commit") != commit:
        return None
    return data
