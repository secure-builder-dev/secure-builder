# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The lifecycle state machine and orientation (spec 03 §3).

Two nested units — a unit of work (a branch, one merge, one gate series) and
the items within it — with state stored in the item and unit files themselves,
in a structured header, not in a separate tracking system. Items declare true
ordering dependencies; a dependency in review counts as satisfied. Every item
carries one sentence stating an observable outcome that constitutes completion.

`orient` reports current position and exactly one next action, derived from
version control (the *remote* protected branch), the item files and CI status
— never from a handoff or status file written by an earlier session. It always
exits successfully; it is a reporter, not a check.
"""
import pathlib
import re

from . import gitutil
from .records import gatelog

UNIT_STATES = ("planned", "building", "in review", "merged")
ITEM_STATES = ("open", "claimed", "in review", "done")
UNITS_DIR = "plans/units"
ITEMS_DIR = "tickets"
IMPLEMENT_SHAPED = re.compile(r"(?i)^\s*(implement|build|create|add|write|develop|make|do)\b")


def read_header(path):
    out = {}
    if not pathlib.Path(path).is_file():
        return out
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            break
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def write_header(path, header, body=""):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{k}: {v}\n" for k, v in header.items()) + "\n" + body
    path.write_text(text, encoding="utf-8", newline="\n")


def set_header(path, key, value):
    path = pathlib.Path(path)
    text = path.read_text(encoding="utf-8")
    head, _, body = text.partition("\n\n")
    lines = head.splitlines()
    for i, l in enumerate(lines):
        if re.match(rf"^{re.escape(key)}\s*:", l):
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.append(f"{key}: {value}")
    path.write_text("\n".join(lines) + "\n\n" + body, encoding="utf-8", newline="\n")


def validate_done_when(sentence):
    s = (sentence or "").strip()
    if not s:
        return "an item carries one sentence stating the observable outcome that constitutes completion"
    if IMPLEMENT_SHAPED.match(s):
        return "the definition of done must be an observable outcome a person could check, not 'implement X'"
    if s.count(". ") > 1:
        return "the definition of done is a single sentence"
    return None


def create_item(root, item_id, unit, done_when, depends_on=()):
    err = validate_done_when(done_when)
    if err:
        raise ValueError(err)
    p = pathlib.Path(root) / ITEMS_DIR / f"{item_id}.md"
    if p.exists():
        raise ValueError(f"{item_id} already exists")
    write_header(p, {"id": item_id, "unit": unit, "state": "open", "depends_on": ", ".join(depends_on) or "-",
                     "done_when": done_when}, f"# {item_id}\n")
    return p


def unit_from_branch(branch):
    """The unit-of-work identifier a branch carries: its last path segment, so `unit/U1`
    and `U1` name the same unit and the identifier is usable as a file name."""
    return branch.rsplit("/", 1)[-1].strip() or branch


def create_unit(root, unit_id):
    p = pathlib.Path(root) / UNITS_DIR / f"{unit_id}.md"
    if p.exists():
        raise ValueError(f"{unit_id} already exists")
    write_header(p, {"id": unit_id, "state": "planned"}, f"# {unit_id}\n")
    return p


def items(root):
    d = pathlib.Path(root) / ITEMS_DIR
    return {p.stem: read_header(p) for p in sorted(d.glob("*.md"))} if d.is_dir() else {}


def dependencies_satisfied(item, all_items):
    deps = [d.strip() for d in item.get("depends_on", "-").split(",") if d.strip() and d.strip() != "-"]
    blocked = []
    for d in deps:
        dep = all_items.get(d)
        if dep is None:
            blocked.append(f"{d} (does not exist)")
        elif dep.get("state") not in ("in review", "done"):
            blocked.append(f"{d} ({dep.get('state', 'unknown')})")
    return blocked


def transition_item(root, item_id, new_state):
    all_items = items(root)
    if item_id not in all_items:
        raise ValueError(f"{item_id} does not exist")
    if new_state not in ITEM_STATES:
        raise ValueError(f"state must be one of {ITEM_STATES}")
    item = all_items[item_id]
    order = ITEM_STATES.index
    if order(new_state) != order(item.get("state", "open")) + 1:
        raise ValueError(f"{item_id}: {item.get('state')} -> {new_state} is not the next state")
    if new_state == "claimed":
        blocked = dependencies_satisfied(item, all_items)
        if blocked:
            raise ValueError(f"{item_id} is blocked by: {', '.join(blocked)}")
    set_header(pathlib.Path(root) / ITEMS_DIR / f"{item_id}.md", "state", new_state)
    return new_state


def transition_unit(root, unit_id, new_state):
    p = pathlib.Path(root) / UNITS_DIR / f"{unit_id}.md"
    h = read_header(p)
    if not h:
        raise ValueError(f"unit {unit_id} does not exist")
    if new_state not in UNIT_STATES or UNIT_STATES.index(new_state) != UNIT_STATES.index(h.get("state", "planned")) + 1:
        raise ValueError(f"{unit_id}: {h.get('state')} -> {new_state} is not the next state")
    set_header(p, "state", new_state)
    return new_state


def orient(root, cfg, ci_status=None):
    """Lines describing position and exactly one next action. Never raises for a
    reportable condition; the caller always exits 0."""
    root = pathlib.Path(root)
    L = []
    if not gitutil.is_repo(root):
        return ["position: not a git repository", "next: initialise version control"]
    branch = gitutil.current_branch(root)
    head = gitutil.head(root)
    protected = cfg.protected_branch if cfg else "main"
    remote_ref = f"origin/{protected}"
    remote = gitutil.rev(root, remote_ref)
    if remote:
        ahead = len(gitutil.commits_in(root, remote_ref, head))
        behind = len(gitutil.commits_in(root, head, remote_ref))
        L.append(f"position: branch {branch} at {head[:12]}; {ahead} ahead of / {behind} behind {remote_ref}")
    else:
        L.append(f"position: branch {branch} at {head[:12]}; remote protected branch {remote_ref} not present — cannot compare "
                 "(a local copy of the protected branch is not consulted; it drifts)")
    L.append(f"ci: {ci_status or 'not configured'}")
    unit = unit_from_branch(branch)
    unit_hdr = read_header(root / UNITS_DIR / f"{unit}.md")
    all_items = items(root)
    mine = {k: v for k, v in all_items.items() if v.get("unit") == unit}
    rows, _ = gatelog.series(root)
    runs = [r for r in rows if r["unit"] == unit]
    L.append(f"unit: {unit} state={unit_hdr.get('state', 'no unit file')}; items: "
             + ", ".join(f"{k}={v.get('state')}" for k, v in mine.items()) if mine else f"unit: {unit} state={unit_hdr.get('state', 'no unit file')}; items: none")
    if runs:
        last = runs[-1]
        L.append(f"last gate: run {last['run']} {last['verdict']} ({last['findings']} findings)")
    # exactly one next action
    if branch == protected:
        nxt = "branch from the remote protected branch to start a unit of work"
    elif unit_hdr.get("state") == "merged":
        nxt = "unit is merged: close it and start the next"
    elif unit_hdr.get("state") == "in review":
        nxt = "await the gate verdict and the human merge; do not push further commits to this unit" if runs and runs[-1]["verdict"] == "pass" else "address the gate findings, then re-run the handoff"
    elif any(v.get("state") == "claimed" for v in mine.values()):
        k = next(k for k, v in mine.items() if v.get("state") == "claimed")
        nxt = f"continue {k}: {mine[k].get('done_when', '')}"
    else:
        ready = [k for k, v in mine.items() if v.get("state") == "open" and not dependencies_satisfied(v, all_items)]
        if ready:
            nxt = f"claim {ready[0]}: {mine[ready[0]].get('done_when', '')}"
        elif mine and all(v.get("state") in ("in review", "done") for v in mine.values()):
            nxt = "all items done: run the scan, then generate the handoff"
        elif mine:
            nxt = "every open item is blocked by a dependency: resolve the blocking item first"
        else:
            nxt = "no items for this unit: cut work items with a definition of done"
    L.append(f"next: {nxt}")
    return L
