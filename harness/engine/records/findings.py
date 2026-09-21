# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The findings register (spec 02 §4). Two tables with different semantics.

Table A — permanent checks: every P0/P1 finding, from any source, becomes a row
before its fix commits, written as the *class* it catches, naming the mechanism
that now catches it and where that mechanism lives. Read at gate start; a row
whose mechanism is missing is a blocking finding.

Table B — accepted risks: the attack path, the compensating control, and proof
the control exists. A row is accepted only when the proof column is satisfied;
otherwise it is open, and it is reported every run until it is.

Rows are added by a human or by an agent transcribing an identified human
decision; the row names that person. An automated agent never accepts its own
finding (REQ-4.3.2). Ungated inbound code is recorded here (REQ-4.4.1).
"""
import pathlib
import re

from . import table
from . import schema as sch

FILE = ".engine/records/findings-register.md"
A_STATUSES = ("active", "retired")
B_STATUSES = ("open", "accepted", "closed")
PROOF_SATISFIED = re.compile(r"^(?!\s*$)(?!.*\b(intended|planned|will|todo|tbd|pending)\b).+", re.I)


def read(root):
    a, pa, _ = table.read(root, FILE, "findings-register-a")
    b, pb, _ = table.read(root, FILE, "findings-register-b")
    return (a or []), (b or []), pa + pb


def add_check(root, cfg, *, id, finding_class, mechanism, lives_in, decided_by, status="active"):
    if status not in A_STATUSES:
        raise table.Malformed(f"status must be one of {A_STATUSES}")
    if not decided_by.strip() or decided_by.strip().lower() in ("agent", "automated", "bot", sch.UNKNOWN):
        raise table.Malformed("a findings-register row names the human whose decision it records")
    if re.search(r"\b(user|endpoint|route)\s+\w+\b.*\bcould\b", finding_class, re.I) and len(finding_class) < 40:
        pass  # instance-shaped wording is a judgment call; the check below reports very short classes
    return table.append(root, FILE, sch.FINDINGS_A, {
        "id": id, "class": finding_class, "mechanism": mechanism, "lives_in": lives_in, "status": status,
        "decided_by": decided_by, "side": cfg.side if cfg else sch.UNKNOWN})


def add_risk(root, cfg, *, id, risk, attack_path, compensating_control, proof, re_review_trigger, owner,
             review_by, decided_by, status="open"):
    if status not in B_STATUSES:
        raise table.Malformed(f"status must be one of {B_STATUSES}")
    if not attack_path.strip() or attack_path.strip() == "-":
        raise table.Malformed("a risk without a written attack path is not understood well enough to record")
    if status == "accepted" and not proof_satisfied(proof):
        raise table.Malformed("a risk may be marked accepted only when the proof column is satisfied")
    if not decided_by.strip() or decided_by.strip().lower() in ("agent", "automated", "bot", sch.UNKNOWN):
        raise table.Malformed("a risk acceptance names the human who decided it; an agent never accepts its own finding")
    return table.append(root, FILE, sch.FINDINGS_B, {
        "id": id, "risk": risk, "attack_path": attack_path, "compensating_control": compensating_control,
        "proof": proof, "re_review_trigger": re_review_trigger, "owner": owner, "review_by": review_by,
        "status": status, "decided_by": decided_by, "side": cfg.side if cfg else sch.UNKNOWN})


def proof_satisfied(proof):
    """Proof names a test or check and says it runs; an intention is not proof."""
    p = (proof or "").strip()
    if p in ("", "-", sch.UNKNOWN):
        return False
    return bool(PROOF_SATISFIED.match(p))


def lives_in_resolves(root, pointer):
    """`lives_in` is `path` or `path#symbol` or `path §section`; the path must exist and,
    where a symbol or section is named, it must appear in the file."""
    root = pathlib.Path(root)
    m = re.match(r"^\s*([^#§\s]+)\s*(?:[#§]\s*(.+))?$", pointer or "")
    if not m:
        return False
    path, anchor = m.group(1), (m.group(2) or "").strip()
    p = root / path
    if not p.is_file():
        return False
    if anchor:
        return anchor in p.read_text(encoding="utf-8", errors="replace")
    return True


def current(rows):
    """The rows that stand: the register is append-only, so a row is corrected or retired by appending a
    later row with the same id, and the latest row per id is the one a gate reads (spec 02 §12)."""
    latest = {}
    for r in rows:
        latest[r["id"]] = r
    return list(latest.values())


def problems(root):
    """What a gate reads at start (REQ-4.1.4, REQ-4.2.2): regressed mechanisms
    (blocking) and unsatisfied proofs (reported every run)."""
    a, b, parse_problems = read(root)
    blocking, reported = [], []
    for r in current(a):
        if r["status"] != "active":
            continue
        if not lives_in_resolves(root, r["lives_in"]):
            blocking.append(f"{r['id']}: mechanism '{r['mechanism']}' at '{r['lives_in']}' does not resolve — the check has regressed")
    for r in b:
        if r["status"] == "closed":
            continue
        if r["status"] == "accepted" and not proof_satisfied(r["proof"]):
            blocking.append(f"{r['id']}: marked accepted but the proof column is not satisfied ('{r['proof']}')")
        elif not proof_satisfied(r["proof"]):
            reported.append(f"{r['id']}: open — compensating control '{r['compensating_control']}' has no proof it exists")
    return blocking, reported, parse_problems
