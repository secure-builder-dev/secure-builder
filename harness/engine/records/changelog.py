# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The governance changelog (spec 02 §5; spec 01 §11.8). One row per change to
the rule set, written before the commit. The sign-off records what the human
was shown, not merely that approval occurred; a row written after the fact says
so; a change that rode along with an authorized one is called out so it can be
reverted independently."""
import re

from . import now, table
from . import schema as sch

FILE = ".engine/records/governance-changelog.md"
SHOWN = re.compile(r"\b(shown|showed|hunk|diff|lines?\s+\d|text below|literal)\b", re.I)


def add(root, cfg, *, change_id, file_section, base_commit, result_commit, grounding, sign_off,
        retroactive=False, rode_along="-"):
    if not SHOWN.search(sign_off or ""):
        raise table.Malformed("sign_off must record what the human was shown (e.g. 'approved after being shown hunks 1-2'), "
                              "not merely that approval occurred")
    if not re.fullmatch(r"[0-9a-f]{7,40}|pending", base_commit):
        raise table.Malformed("base_commit must be a commit identifier")
    if not re.fullmatch(r"[0-9a-f]{7,40}|pending", result_commit):
        raise table.Malformed("result_commit must be a commit identifier, or 'pending' when the row precedes the commit")
    return table.append(root, FILE, sch.GOVERNANCE, {
        "date": now(cfg), "change_id": change_id, "file_section": file_section, "base_commit": base_commit,
        "result_commit": result_commit, "grounding": grounding, "sign_off": sign_off,
        "retroactive": "yes" if retroactive else "no", "rode_along": rode_along or "-",
        "side": cfg.side if cfg else sch.UNKNOWN})


def read(root):
    rows, problems, _ = table.read(root, FILE, "governance-changelog")
    return rows or [], problems
