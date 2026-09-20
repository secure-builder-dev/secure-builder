# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The command line. `python -m engine <command>`.

  check [--json]      run every mechanical check and the self-test suite — the
                      single command CI also runs (spec 01 REQ-3.1.1); needs no
                      credentials and no network (REQ-3.1.2)
  init ...            write the project configuration once (spec 01 §2)
  config              print the configuration and its problems
  degradation         print the honest-degradation statement (spec 04 §7)
  version             print the content-derived harness version
  update --project P [--dry-run]   place or refresh the harness in a project (spec 06)
  adopt --project P   adopt into an existing project and inventory pre-existing code
  ownership           print the four ownership classes
  audit               the standing self-test audit (spec 05 §10); reports, never blocks
  integration         run the integration tier with the real external tools (spec 05 §6.1)
  check --reverse-tests   run the self-test suite in reverse order (order independence)
  coverage            measure the harness's own self-test coverage (standard library only)
  credential-scan --staged   the credential check against the staged index, for a pre-commit hook
  accept-directive KEY "reason" "by"   accept a risky configuration directive into the baseline
"""
import io
import json
import pathlib
import sys
import unittest

from . import config as cfgmod
from . import audit, coverage, degradation, distribute, integration, ownership, version
from .checks import run_all
from .outcome import Summary


def cmd_check(root, argv):
    as_json = "--json" in argv
    outcomes = []
    cfg = None
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError:
        pass
    outcomes = run_all(root, cfg)
    for o in outcomes:
        for line in o.lines():
            print(line)
    summary = Summary(outcomes, na_threshold=cfg.na_threshold if cfg else 0.5)
    print(summary.line())
    for line in summary.disposition_lines():
        print(line)

    st = run_selftests(root, reverse="--reverse-tests" in argv)
    print(f"[selftest] {st['pass']} passed, {st['fail']} failed, {st['skip']} skipped"
          + (f" (skipped: {', '.join(st['skips'])})" if st["skips"] else ""))
    if st["pass"] + st["fail"] + st["skip"] == 0:
        print("[selftest] COULD NOT RUN: zero test cases discovered — an uninvoked suite is an absent suite")

    code = summary.exit_code
    if st["fail"] or (st["pass"] + st["fail"] + st["skip"] == 0):
        code = max(code, 1)
    if cfg:
        print(cfg.mode_line())
    print(f"harness version: {version()}")
    if as_json:
        print(json.dumps({
            "version": version(),
            "mode": cfg.mode if cfg else None,
            "checks": [{"check": o.check, "state": o.state.value, "blocking": o.blocking,
                        "findings": o.findings} for o in outcomes],
            "counts": {"applicable": summary.applicable, "not_applicable": summary.not_applicable,
                       "nothing_yet": summary.nothing_yet, "deferred": summary.deferred,
                       "failed": summary.failed},
            "selftest": st,
            "exit": code,
        }))
    print(f"check: {'GREEN' if code == 0 else 'RED'} (exit {code})")
    return code


SELFTEST_PATTERN = "test_*.py"


def discover_selftests(root):
    """The suite the check command runs. Discovery, not a hand-maintained list."""
    suite_dir = pathlib.Path(root) / "selftest"
    if not suite_dir.is_dir():
        return None
    return unittest.TestLoader().discover(str(suite_dir), pattern=SELFTEST_PATTERN, top_level_dir=str(root))


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def run_selftests(root, reverse=False):
    """Run the hermetic self-test suite and report pass/fail/skip separately (spec 05 REQ-9.4)."""
    suite = discover_selftests(root)
    if suite is None:
        return {"pass": 0, "fail": 0, "skip": 0, "skips": []}
    if reverse:
        suite = unittest.TestSuite(list(_flatten(suite))[::-1])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    failed = len(result.failures) + len(result.errors)
    for kind, items in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in items:
            print(f"[selftest] {kind}: {test.id()}")
            print("    " + "\n    ".join(tb.strip().splitlines()[-4:]))
    skips = [t.id().split(".")[-1] for t, _ in result.skipped]
    return {"pass": result.testsRun - failed - len(result.skipped), "fail": failed,
            "skip": len(result.skipped), "skips": skips}


def cmd_init(root, argv):
    kw = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            kw[k.replace("-", "_")] = v
    if "track" not in kw or "mode" not in kw:
        print("init: track=<web|android> mode=<connected|local|disconnected> are required; "
              "optional: tier= provider= app_type= topology= side= operators= protected_branch= timezone= clock=")
        return 2
    try:
        cfg = cfgmod.init(root, **kw)
    except (cfgmod.ConfigError, TypeError) as e:
        print(f"init: REFUSED — {e}")
        return 1
    print(f"init: wrote {cfgmod.CONFIG_PATH}: {cfg.shape}; {cfg.mode_line()}")
    return 0


def cmd_config(root, argv):
    try:
        cfg = cfgmod.load(root)
    except cfgmod.ConfigError as e:
        print(f"config: {e}")
        return 1
    print(json.dumps(cfg.data, indent=2))
    for p in cfg.problems():
        print(f"problem: {p}")
    for a in cfg.unset_axes():
        print(f"not yet chosen: {a}")
    return 0


def cmd_degradation(root, argv):
    try:
        print(degradation.statement(root))
    except cfgmod.ConfigError as e:
        print(f"degradation: COULD NOT RUN — {e}")
        return 2
    return 0


def _project(root, argv):
    if "--project" in argv:
        return pathlib.Path(argv[argv.index("--project") + 1]).resolve()
    return root


def cmd_update(root, argv):
    project = _project(root, argv)
    if not project.is_dir():
        print(f"update: COULD NOT RUN — {project} is not a directory")
        return 2
    s = distribute.update(project, dry_run="--dry-run" in argv)
    for line in s.lines():
        print(line)
    print(f"update: project {project} carries harness version {distribute.recorded_version(project) or '(report only)'}")
    return 0


def cmd_adopt(root, argv):
    project = _project(root, argv)
    if not project.is_dir():
        print(f"adopt: COULD NOT RUN — {project} is not a directory")
        return 2
    s, n = distribute.adopt(project)
    for line in s.lines():
        print(line)
    print(f"adopt: {n} pre-existing file(s) inventoried as never assessed in "
          f"{ownership.ENGINE_DIR}/records/adoption-inventory.md; each needs a disposition")
    return 0


def cmd_audit(root, argv):
    from .checks import REGISTRY
    lines, total, could_not = audit.run(root, REGISTRY)
    for line in lines:
        print(line)
    return 2 if could_not else 0


def cmd_integration(root, argv):
    code, lines = integration.run(root)
    for line in lines:
        print(line)
    print(f"integration: {'PASSED' if code == 0 else 'NOT VERIFIED' if code == 2 else 'FAILED'} (exit {code})")
    return code


def cmd_coverage(root, argv):
    def suite():
        run_selftests(root)
    rep = coverage.collect(root, suite)
    tot = sum(v["total"] for v in rep["files"].values())
    cov = sum(v["covered"] for v in rep["files"].values())
    print(f"coverage: {cov}/{tot} executable lines ({(100.0 * cov / tot) if tot else 0:.1f}%) across {len(rep['files'])} harness modules -> .engine/local/coverage.json")
    return 0 if tot else 2


def cmd_credential_scan(root, argv):
    from .checks import credential_scan
    if "--staged" in argv:
        scanned, findings = credential_scan.scan_staged(root)
        for f in findings:
            print(f"    - {f}")
        print(f"[credential-scan] staged: {scanned} file(s), {len(findings)} finding(s)")
        return 1 if findings else 0
    o = credential_scan.run(root, None)
    for line in o.lines():
        print(line)
    return o.exit_code


def cmd_accept_directive(root, argv):
    from .checks import attack_surface
    if len(argv) < 3:
        print("accept-directive KEY \"reason\" \"by\" — KEY is path:kind as the check reports it")
        return 2
    attack_surface.accept(root, argv[0], argv[1], argv[2])
    print(f"accept-directive: {argv[0]} accepted by {argv[2]} — {argv[1]}")
    return 0


def cmd_ownership(root, argv):
    for name, table in ownership.classes():
        print(f"## {name}")
        for k in (table if isinstance(table, list) else table):
            print(f"  {k}")
    return 0


COMMANDS = {"check": cmd_check, "init": cmd_init, "config": cmd_config,
            "degradation": cmd_degradation, "version": lambda r, a: (print(version()), 0)[1],
            "update": cmd_update, "adopt": cmd_adopt, "ownership": cmd_ownership,
            "audit": cmd_audit, "integration": cmd_integration, "coverage": cmd_coverage,
            "credential-scan": cmd_credential_scan, "accept-directive": cmd_accept_directive}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    root = pathlib.Path(".").resolve()
    if "--root" in argv:
        i = argv.index("--root")
        root = pathlib.Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](root, argv[1:])


if __name__ == "__main__":
    sys.exit(main())
