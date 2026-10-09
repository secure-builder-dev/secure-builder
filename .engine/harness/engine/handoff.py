# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The handoff (spec 03 §2; spec 01 §3.3; spec 02 §3.5).

The transition from building to reviewing happens through a generated artifact
whose entire content is derivable from version control and project
configuration. There is no free-text field: nothing typed by a person can
cross the wall. The generator refuses when its preconditions are unmet — no
scan stamp for this exact commit, or a stamp that is not green — and the only
override is for a scan that was *impossible*, never for one that failed. It
writes the started marker before any verdict exists.
"""
import json
import pathlib
import re

from . import lifecycle, gitutil, stamp
from .records import gatelog

READ_FIRST = ["AGENTS.md", ".engine/rules/RULES.md", ".engine/rules/agents/security-gate.md",
              ".engine/rules/control-manifest.json", ".engine/records/findings-register.md"]
WORK_ITEM = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b|(?<![\w/])#(\d+)\b")


class HandoffRefused(Exception):
    pass


def next_run(root, unit):
    rows, _ = gatelog.series(root)
    runs = [int(r["run"]) for r in rows if r["unit"] == unit and r["run"].isdigit()]
    marks = [int(m["run"]) for m in gatelog.started_markers(root) if m.get("unit") == unit and str(m.get("run", "")).isdigit()]
    return max(runs + marks + [0]) + 1


def unit_items(root, unit, messages):
    """The work items of a unit: the item files whose header names it. Commit messages are scraped only when no
    item file does (antipode and daynight handoffs listed control ids, governance rows and 'UTF-8' as work items
    and missed the single-letter items A-1 and D-1)."""
    named = sorted(k for k, v in lifecycle.items(root).items() if v.get("unit") == unit)
    if named:
        return named, [f"tickets/{i}.md" for i in named]
    scraped = sorted({(m.group(1) or ("#" + m.group(2))) for s in messages for m in WORK_ITEM.finditer(s)})
    return scraped, [f"tickets/{i}.md" for i in scraped if (pathlib.Path(root) / "tickets" / f"{i}.md").is_file()]


def generate(root, cfg, *, checkpoint=False, scan_impossible=False, scan_impossible_reason=""):
    """Build the handoff. Raises HandoffRefused with the reason when preconditions fail."""
    root = pathlib.Path(root)
    if not gitutil.is_repo(root):
        raise HandoffRefused("not a git repository")
    head = gitutil.head(root)
    branch = gitutil.current_branch(root)
    protected = gitutil.protected_ref(root, cfg.protected_branch)
    if not protected:
        raise HandoffRefused(f"protected branch '{cfg.protected_branch}' is not present locally or on the remote")
    if branch == cfg.protected_branch:
        raise HandoffRefused(f"HEAD is the protected branch '{cfg.protected_branch}'; a handoff is generated on a unit-of-work branch")
    base = gitutil.rev(root, protected)
    merge_base = gitutil.merge_base(root, protected, head)
    if not merge_base:
        raise HandoffRefused("no merge base with the protected branch")
    commits = gitutil.commits_in(root, merge_base, head)
    if not commits:
        raise HandoffRefused("the range is empty: nothing to review")
    changed = gitutil.changed_files(root, merge_base, head)

    # scan precondition (spec 01 REQ-3.3.1–3.3.2)
    st = stamp.for_commit(root, head)
    scan_line = None
    if st is None:
        raw = stamp.read(root)
        if raw is not None and raw.get("verdict") == "red" and raw.get("commit") == head:
            raise HandoffRefused("the scan for this commit is red; the override exists for an impossible scan, not a failed one")
        if not scan_impossible:
            raise HandoffRefused(f"no scan stamp describes this exact commit {head[:12]}; run the scan first "
                                 "(or, only where scanning is impossible here, pass the impossible-scan override with a reason)")
        if not scan_impossible_reason.strip():
            raise HandoffRefused("the impossible-scan override requires a reason")
        scan_line = f"scan: NOT PERFORMED — override in effect: scan impossible in this environment ({scan_impossible_reason.strip()})"
    else:
        if st["verdict"] == "red":
            if scan_impossible:
                raise HandoffRefused("the scan for this commit is red; the override exists for an impossible scan, not a failed one")
            raise HandoffRefused("the scan for this commit is red; fix on the branch, rescan, then hand off")
        if st["verdict"] == "unverified":
            scan_line = f"scan: UNVERIFIED for {head[:12]} (detection-data age could not be determined; override marked the verdict unverified)"
        else:
            scan_line = f"scan: green for {head[:12]}; scanners: {', '.join(st['scanners'])}"

    unit = lifecycle.unit_from_branch(branch)
    run = next_run(root, unit)
    items, item_files = unit_items(root, unit, gitutil.log_subjects(root, merge_base, head))
    marker = gatelog.write_started(root, cfg, unit, run, f"{merge_base[:12]}..{head[:12]}", head,
                                   extra={"checkpoint": checkpoint})
    doc = {
        "kind": "advisory checkpoint" if checkpoint else "gate handoff",
        "unit": unit, "run": run,
        "range": {"base": merge_base, "head": head, "protected_ref": protected,
                  "merge_base_differs_from_protected": merge_base != base},
        "commit_count": len(commits), "changed_file_count": len(changed),
        "work_items": items, "work_item_files": item_files,
        "shape": {"track": cfg.track, "tier": cfg.tier, "provider": cfg.provider, "app_type": cfg.app_type,
                  "mode": cfg.mode, "topology": cfg.topology, "side": cfg.side},
        "read_first": READ_FIRST,
        "scan": scan_line,
        "started_marker": marker.relative_to(root).as_posix(),
        "instruction": ("Run the quality gate, then the security gate, on the range above. Read the diff from version "
                        "control. Do not read the conversation in which this code was written. "
                        + ("This is an advisory checkpoint: findings only, no merge implication." if checkpoint
                           else "End with the verdict block.")),
    }
    return doc


def render(doc):
    L = [f"# {doc['kind'].upper()}: {doc['unit']} run {doc['run']}", "",
         f"range: {doc['range']['base']}..{doc['range']['head']}",
         f"protected ref: {doc['range']['protected_ref']}"
         + (" (merge base differs from the protected tip)" if doc["range"]["merge_base_differs_from_protected"] else ""),
         f"commits: {doc['commit_count']}; changed files: {doc['changed_file_count']}",
         f"unit of work: {doc['unit']}",
         f"work items: {', '.join(doc['work_items']) or '(none named in commit messages)'}",
         f"work item files: {', '.join(doc['work_item_files']) or '(none)'}",
         "shape: " + " ".join(f"{k}={v}" for k, v in doc["shape"].items()),
         "read first: " + ", ".join(doc["read_first"]),
         doc["scan"], f"started marker: {doc['started_marker']}", "",
         doc["instruction"], "",
         "This handoff carries no free-text field. Its content is derived from version control and the",
         "project configuration and nothing else.", ""]
    return "\n".join(L)


def write(root, doc):
    d = pathlib.Path(root) / ".engine" / "work"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"handoff-{doc['unit']}-{doc['run']}.md"
    p.write_text(render(doc), encoding="utf-8", newline="\n")
    (d / f"handoff-{doc['unit']}-{doc['run']}.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                                                                 encoding="utf-8", newline="\n")
    return p
