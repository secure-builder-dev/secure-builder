# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Coverage thresholds on the range (spec 01 REQ-5.1.1–5.1.2, REQ-10.1).

The range is the protected branch (as the remote sees it) to HEAD. On the
protected branch itself there is no range under review. A missing report is
"could not run": coverage that was not measured is not coverage.
"""
from .. import coverage, gitutil
from ..outcome import Outcome

NAME = "coverage-range"
DEFAULT_REPORT = ".engine/local/coverage.json"


def run(root, cfg, base=None, head=None):
    if not gitutil.is_repo(root):
        return Outcome.could_not_run(NAME, "not a git repository; no range can be determined")
    if base is None:
        protected = cfg.protected_branch if cfg else "main"
        ref = gitutil.protected_ref(root, protected)
        if not ref:
            return Outcome.could_not_run(NAME, f"protected branch '{protected}' is not present locally or on the remote")
        head = head or gitutil.head(root)
        if gitutil.rev(root, ref) == head:
            return Outcome.nothing_yet(NAME, "range under review", f"HEAD is the protected branch ({ref}); coverage is evaluated on branches")
        base = gitutil.merge_base(root, ref, head) or ref
    changed = gitutil.changed_files(root, base, head)
    report_path = (cfg.get("coverage_report") if cfg else None) or DEFAULT_REPORT
    report = coverage.read_report(root / report_path if not str(report_path).startswith("/") else report_path)
    thresholds = (cfg.get("coverage_thresholds") if cfg else None) or coverage.DEFAULT_THRESHOLDS
    assessed, findings = coverage.evaluate(changed, report or {}, thresholds)
    if assessed == 0:
        return Outcome.nothing_yet(NAME, "changed source files in the range", f"{len(changed)} changed file(s), none is application source")
    if report is None:
        return Outcome.could_not_run(NAME, f"no coverage report at {report_path}; {assessed} changed source file(s) unmeasured")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} of {assessed} changed source files below threshold or unmeasured", findings, blocking=True)
    return Outcome.clean(NAME, f"{assessed} changed source file(s) in {base[:7]}..{head[:7]} meet their layer thresholds")
