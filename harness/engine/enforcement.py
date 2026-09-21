# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Enforcement points for the non-negotiables (spec 03 REQ-1.2.3).

Precedence prose has persuasive force and no mechanical force. Every
non-negotiable in the rulebook therefore names where it is enforced outside
the repository's text — branch protection, the pre-execution guard, the
pre-commit hook, a registered mechanical check, or a structural property of a
generator — and this module verifies that each named point exists. A rule
that appears in the rulebook with no entry here is reported: it is advisory,
however it is worded.
"""
import pathlib
import re

from . import guard, handoff
from .checks import REGISTRY
from .outcome import Outcome

NAME = "enforcement"
RULES = "engine/dist/rules/RULES.md"
# where the rulebook and the shipped hook live: in the harness source tree, and in a placed project
LAYOUTS = [
    {"package": "harness/engine", "rules": "harness/engine/dist/rules/RULES.md", "pre_commit": "harness/engine/dist/hooks/pre-commit.py"},
    {"package": "engine", "rules": "engine/dist/rules/RULES.md", "pre_commit": "engine/dist/hooks/pre-commit.py"},
    {"package": ".engine/harness/engine", "rules": ".engine/rules/RULES.md", "pre_commit": ".engine/harness/hooks/pre-commit.py"},
]

# rule number -> [(kind, where, how it is verified)]. A `platform:` point is enforced by the
# hosting platform or the agent runtime and cannot be verified from inside the repository; it is
# listed, never counted, and every rule needs at least one point this module can verify.
POINTS = {
    1: [("platform", "branch protection on the protected branch (spec 03 REQ-4.1; recorded 'not achieved' where absent)", "platform:branch-protection"),
        ("guard-hook", "guard.blocks refuses a push to / merge on the protected branch (shipped as .engine/harness/hooks/guard.py)", "guard:push"),
        ("mechanical-check", "run_attestation: a gate row exists for every range that reached the protected branch", "check:run_attestation")],
    2: [("mechanical-check", "gate._attribution on every gated range", "gate:_attribution"),
        ("mechanical-check", "harness_self_scan on the harness's own tree", "check:harness_self_scan")],
    3: [("mechanical-check", "credential_scan: a reproduced secret cannot land in the repository", "check:credential_scan"),
        ("mechanical-check", "gate._frozen_surface reports the frozen surface as counts, values not shown", "gate:_frozen_surface"),
        ("platform", "the agent runtime's read deny-list for value and variable files (spec 03 REQ-4.4)", "platform:runtime-denylist")],
    4: [("structural", "the handoff has no free-text field: handoff.generate takes none", "handoff:no-free-text"),
        ("structural", "review launches a fresh process whose only input is the handoff path (cmd_review)", "cli:cmd_review")],
    5: [("mechanical-check", "governance.check_range on every gated range: a governed change without its changelog row is blocking", "gate:governance.check_range"),
        ("pre-commit-hook", "the shipped pre-commit refuses a staged governance change without its row", "dist-hook:staged_problems")],
    6: [("mechanical-check", "negative_fixtures: a registered check without a failing self-test is blocking", "check:negative_fixtures")],
    7: [("mechanical-check", "findings_register: a finding without a mechanism or checklist line is reported", "check:findings_register")],
}


def layout(root):
    root = pathlib.Path(root)
    for lay in LAYOUTS:
        if (root / lay["rules"]).is_file() and (root / lay["package"] / "checks").is_dir():
            return lay
    return None


def rules_in_text(root):
    lay = layout(root)
    if lay is None:
        return None
    p = pathlib.Path(root) / lay["rules"]
    section, out = False, []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line.strip() == "## Non-negotiables"
            continue
        m = re.match(r"^(\d+)\.\s", line)
        if section and m:
            out.append(int(m.group(1)))
    return out


def _read(root, rel):
    p = pathlib.Path(root) / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def _exists(root, how):
    """True when the named enforcement point exists in this harness; None for a platform point."""
    lay = layout(root)
    pkg = lay["package"]
    kind, _, arg = how.partition(":")
    if kind == "platform":
        return None
    if kind == "check":
        return arg in REGISTRY and (pathlib.Path(root) / pkg / "checks" / f"{arg}.py").is_file()
    if kind == "guard":
        return guard.blocks("git push origin main", "main", "feature") is not None and guard.blocks("git merge feature", "main", "main") is not None
    if kind == "gate":
        return f"def {arg}(" in _read(root, f"{pkg}/gate.py") or f"{arg}(" in _read(root, f"{pkg}/gate.py")
    if kind == "handoff":
        import inspect
        params = inspect.signature(handoff.generate).parameters
        return not any(k in n.lower() for n in params for k in ("note", "free", "comment", "message", "text"))
    if kind == "cli":
        return f"def {arg}(" in _read(root, f"{pkg}/__main__.py")
    if kind == "dist-hook":
        return arg in _read(root, lay["pre_commit"])
    return False


def problems(root):
    rules = rules_in_text(root)
    if rules is None:
        return None
    out = []
    for n in rules:
        pts = POINTS.get(n)
        if not pts:
            out.append(f"rule {n} exists only as prose: no enforcement point outside the text is recorded for it")
            continue
        verified = 0
        for kind, where, how in pts:
            ok = _exists(root, how)
            if ok is False:
                out.append(f"rule {n}: the recorded {kind} enforcement point ({where}) does not exist")
            elif ok:
                verified += 1
        if not verified and not any("does not exist" in x and x.startswith(f"rule {n}:") for x in out):
            out.append(f"rule {n}: every recorded enforcement point is a platform assertion; none is verifiable from the repository")
    for n in POINTS:
        if n not in rules:
            out.append(f"enforcement is recorded for rule {n} but the rulebook has no such rule")
    return out


def platform_points(root):
    return [(n, where) for n, pts in POINTS.items() for kind, where, how in pts if how.startswith("platform:")]


def run(root, cfg):
    root = pathlib.Path(root)
    if layout(root) is None:
        return Outcome.could_not_run(NAME, "no rulebook beside the harness source to verify")
    probs = problems(root)
    if probs:
        return Outcome.found(NAME, "a non-negotiable rests on prose alone", probs, blocking=True)
    plat = platform_points(root)
    return Outcome.clean(NAME, f"every one of {len(rules_in_text(root))} non-negotiables names a verifiable enforcement point outside the text; "
                               f"{len(plat)} further point(s) are platform assertions the repository cannot verify")
