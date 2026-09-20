# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The governance protocol (spec 01 §11; spec 02 §5).

A governance change is any change to the reviewer's rule set: the project
instruction file, the rulebook, the reviewer definitions, the reference
documents, the control manifest, the configuration that switches checks, and
this protocol's own zone list. For such a change the accountable control is a
human's line-by-line diff review; the automated gate is advisory. Sections an
agent may edit are an explicit allowlist, and within one an agent may only
transcribe a decision approved elsewhere, citing its source. A change declares
its file and section before implementation — in the changelog row that is
mandatory before the commit — lands in its own commit, and is reviewed against
the rule set as it existed at the base commit. Automated maintenance of a
governed document appends grounded entries to a designated section and never
rewrites, reorders or deletes.
"""
import json
import pathlib
import re

from . import gitutil
from .outcome import Outcome
from .records import changelog

ZONES_FILE = ".engine/governance.json"
DEFAULT_SET = ["AGENTS.md", ".engine/rules/", ".engine/agents/", ".engine/reference/", ".engine/control-manifest.json",
               ".engine/config.json", ZONES_FILE]
SOURCE = re.compile(r"\[(source|decision|approved|finding|ticket|grounded):\s*[^\]]+\]", re.I)


def governed_set(root, cfg=None):
    extra = list((cfg.get("governance_set") if cfg else None) or [])
    return DEFAULT_SET + extra


def is_governed(path, gset):
    return any(path == g or (g.endswith("/") and path.startswith(g)) for g in gset)


def zones(root):
    p = pathlib.Path(root) / ZONES_FILE
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return []
    return [z for z in data.get("agent_editable_zones", []) if isinstance(z, dict) and z.get("file") and z.get("section")]


def in_zone(path, section, zs):
    return any(z["file"] == path and z["section"] == section for z in zs)


# --- append-only automated maintenance (REQ-11.7.1) and disposition to a checklist line (§1.4) ---

def append_grounded(root, path, section, line, source):
    """Append one grounded entry under `section` of a governed document. Refuses when the
    zone is not allowlisted, when the entry cites no approved source, or when it would
    do anything but append."""
    if not in_zone(path, section, zones(root)):
        raise PermissionError(f"{path} {section!r} is not an agent-editable zone; adding a zone is itself a governance change")
    if not SOURCE.search(source):
        raise PermissionError("an appended entry must cite an external, already-approved source, e.g. [decision: D-12] or [finding: F-3]")
    p = pathlib.Path(root) / path
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == section)
    except StopIteration:
        raise PermissionError(f"{path} has no section {section!r}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    entry = f"- {line.strip()} {source.strip()}"
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, entry)
    new_text = "\n".join(lines) + "\n"
    # the only permitted difference is one appended line
    old_set, new_set = text.splitlines(), new_text.splitlines()
    if len(new_set) != len(old_set) + 1 or [l for l in new_set if l != entry or new_set.count(entry) > 1] != old_set:
        raise PermissionError("automated maintenance may only append")
    p.write_text(new_text, encoding="utf-8", newline="\n")
    return entry


# --- the range check (gate) and the staged check (hook) ---

def changed_governance(root, base, head, gset):
    return [f for f in gitutil.changed_files(root, base, head) if is_governed(f, gset)]


def rows_for_range(root, base, head):
    rows, _ = changelog.read(root)
    commits = set(gitutil.commits_in(root, base, head)) | {head}
    out = []
    for r in rows:
        if r["result_commit"] == "pending" or any(c.startswith(r["result_commit"]) or r["result_commit"].startswith(c[:7]) for c in commits) \
                or r["base_commit"].startswith(base[:7]) or base.startswith(r["base_commit"][:7]):
            out.append(r)
    return out


def check_range(root, cfg, base, head, unit=""):
    """Outcomes for a range: is it a governance change, and if so was the protocol followed."""
    gset = governed_set(root, cfg)
    changed = changed_governance(root, base, head, gset)
    if not changed:
        return [Outcome.clean("governance", "no governed file changed in the range; the ordinary gate applies")], False
    outs = []
    rows = rows_for_range(root, base, head)
    if not rows:
        outs.append(Outcome.found("governance", f"governance change without a changelog row ({', '.join(changed)})",
                                  ["the row is mandatory before the commit: file and section, base and resulting commit, external grounding, "
                                   "and a sign-off recording what the human was shown — a human decision is the accountable control"],
                                  blocking=True))
    else:
        declared = " ".join(r["file_section"] for r in rows)
        outside = [f for f in changed if f not in declared and not any(f.startswith(d.split(" ")[0]) for d in declared.split(","))]
        if outside:
            outs.append(Outcome.found("governance-surface", "change outside the declared surface",
                                      [f"{f}: not named in the changelog row(s) ({declared})" for f in outside], blocking=True))
        else:
            outs.append(Outcome.clean("governance-surface", f"{len(changed)} governed file(s) all within the declared surface: {declared}"))
        ungrounded = [r["change_id"] for r in rows if r["grounding"].strip() in ("", "-", "unknown")]
        if ungrounded:
            outs.append(Outcome.found("governance-grounding", "governance row without external grounding", ungrounded, blocking=True))
    # isolated commit: every commit touching governance touches only governance
    mixed = []
    for c in gitutil.commits_in(root, base, head):
        files = gitutil.changed_files(root, f"{c}~1", c) if gitutil.rev(root, f"{c}~1") else gitutil.changed_files(root, base, c)
        g = [f for f in files if is_governed(f, gset)]
        files = [f for f in files if f != changelog.FILE]          # the row travels with the change it records
        if g and len(g) != len(files):
            mixed.append(f"{c[:12]}: governance ({', '.join(g)}) bundled with feature work ({', '.join(f for f in files if f not in g)})")
    if mixed:
        outs.append(Outcome.found("governance-isolation", "governance change not in its own commit", mixed, blocking=True))
    else:
        outs.append(Outcome.clean("governance-isolation", "governance changes land in their own commits"))
    outs.append(Outcome.clean("governance-advisory", "this range changes the rule set: the automated gate is advisory and the human "
                                                    "line-by-line review is the accountable control; the reviewer evaluates against the rules at the base commit"))
    return outs, True


def rules_at_base(root, base, gset, out_dir):
    """Materialise the governed files as they were at the base commit (REQ-11.6.1)."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for rel in gitutil.git(root, "ls-tree", "-r", "--name-only", base).stdout.splitlines():
        if is_governed(rel, gset):
            text = gitutil.git(root, "show", f"{base}:{rel}").stdout
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
            written.append(rel)
    return written


def staged_problems(root, cfg):
    """For the project pre-commit hook: staged governance files need a pending changelog row naming them."""
    gset = governed_set(root, cfg)
    staged = [f for f in gitutil.staged_files(root) if is_governed(f, gset)]
    if not staged:
        return []
    rows, _ = changelog.read(root)
    pending = [r for r in rows if r["result_commit"] == "pending"]
    if not pending:
        return [f"governance files staged ({', '.join(staged)}) with no pending changelog row — write the row first "
                "(`governance record ...`), with what the human was shown"]
    declared = " ".join(r["file_section"] for r in pending)
    return [f"{f}: staged but not named in a pending changelog row ({declared})" for f in staged
            if f not in declared and not any(f.startswith(d.split(" ")[0]) for d in declared.split(","))]


def record(root, cfg, *, change_id, file_section, grounding, shown_text, approved_by):
    """Write the changelog row before the commit. The sign-off records the literal text shown."""
    base = gitutil.head(root) or "pending"
    changed = [l for l in shown_text.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    snippet = re.sub(r"\s+", " ", " ".join(changed) if changed else shown_text.strip())[:400]
    sign_off = f"{approved_by} approved after being shown the literal text: \"{snippet}\""
    return changelog.add(root, cfg, change_id=change_id, file_section=file_section, base_commit=base[:12] if base != "pending" else "pending",
                         result_commit="pending", grounding=grounding, sign_off=sign_off)


def staged_diff(root, gset):
    """The literal hunks of staged governance changes, for showing in the approval request."""
    out = []
    for f in gitutil.staged_files(root):
        if is_governed(f, gset):
            out.append(gitutil.git(root, "diff", "--cached", "--", f).stdout)
    return "\n".join(out)
