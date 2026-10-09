# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Coverage thresholds on the range (spec 01 REQ-5.1.1–5.1.2, REQ-10.1).

The range is the protected branch (as the remote sees it) to HEAD. On the
protected branch itself there is no range under review. A missing report is
"could not run": coverage that was not measured is not coverage.
"""
from .. import controlshape, coverage, gitutil
from ..outcome import Outcome

NAME = "coverage-range"
DEFAULT_REPORT = ".engine/work/coverage.json"
vendored = controlshape.vendored     # one rule for what is third-party code


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
    # the placed harness under .engine/ is engine-owned and covered by its own suite, not the project's
    changed = [f for f in gitutil.changed_files(root, base, head) if not f.startswith(".engine/")]
    skipped = [f for f in changed if vendored(f)]
    changed = [f for f in changed if not vendored(f)]
    report_path = (cfg.get("coverage_report") if cfg else None) or DEFAULT_REPORT
    # one report per tool: a project with a Python backend and a TypeScript frontend lists both (ticketer)
    paths = report_path if isinstance(report_path, list) else [report_path]
    parts = [coverage.read_report(root / p if not str(p).startswith("/") else p) for p in paths]
    report = None if any(r is None for r in parts) else {k: v for r in parts for k, v in r.items()}
    report_path = ", ".join(map(str, paths))
    thresholds = (cfg.get("coverage_thresholds") if cfg else None) or coverage.DEFAULT_THRESHOLDS
    assessed, findings = coverage.evaluate(changed, report or {}, thresholds)
    if assessed == 0:
        return Outcome.nothing_yet(NAME, "changed source files in the range", f"{len(changed)} changed file(s), none is application source")
    if report is None:
        return Outcome.could_not_run(NAME, f"no coverage report at {report_path}; {assessed} changed source file(s) unmeasured")
    if findings:
        return Outcome.found(NAME, f"{len(findings)} of {assessed} changed source files below threshold or unmeasured", findings, blocking=True)
    return Outcome.clean(NAME, f"{assessed} changed source file(s) in {base[:7]}..{head[:7]} meet their layer thresholds"
                         + (f"; {len(skipped)} vendored third-party file(s) not measured" if skipped else ""))
