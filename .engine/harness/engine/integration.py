# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The integration tier (spec 05 §6.1).

A second, explicitly separate test tier that executes the real external tools.
The hermetic tier gates every push; this tier gates a version. They are never
merged: the hermetic runner discovers only selftest/, this runner discovers
only integration/. Where the tier cannot run in an environment, the release
record says *not verified in this environment* — never a pass.
"""
import datetime
import io
import pathlib
import platform
import sys
import unittest

from . import layout
from . import tools, version

RECORD = "records/RELEASE-RECORD.md"        # the build repository's records folder; a project's is under .engine/
PATTERN = "itest_*.py"


def runtime():
    """The container runtime available, as (name, version line) or None."""
    for name in ("docker", "podman"):
        if tools.resolve(name):
            res = tools.run_tool(name, ["--version"], timeout=30)
            if res.exit_code == 0:
                return name, res.stdout.strip().splitlines()[0] if res.stdout.strip() else name
    return None


def environment_line(rt):
    return f"{platform.system()} {platform.release()}; python {platform.python_version()}; " + (
        f"{rt[0]}: {rt[1]}" if rt else "no container runtime")


def record_path(root):
    root = pathlib.Path(root)
    return root / RECORD if (root / "records").is_dir() or not (root / ".engine" / "records").is_dir() else root / ".engine" / RECORD


def append_record(root, line):
    p = record_path(root)
    header = ("# Release record\n\n© 2026 Casey Houle. All rights reserved.\n\n"
              "Append-only. One line per integration-tier run, with the environment it ran in.\n\n")
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(header, encoding="utf-8", newline="\n")
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def run(root):
    """Returns (exit code, lines). Exit 0 only when the tier ran and passed."""
    root = pathlib.Path(root)
    today = datetime.date.today().isoformat()
    v = version()
    rt = runtime()
    env = environment_line(rt)
    lines = [f"[integration] environment: {env}", f"[integration] harness version: {v}"]
    if rt is None:
        line = f"- {today} · {v} · integration tier: not verified in this environment ({env})"
        append_record(root, line)
        lines.append("[integration] COULD NOT RUN: no container runtime — recorded as not verified in this environment")
        return 2, lines
    suite_dir = (layout.harness_dir(root) or root) / "integration"
    if not suite_dir.is_dir():
        append_record(root, f"- {today} · {v} · integration tier: not verified in this environment (no integration/ suite; {env})")
        lines.append("[integration] COULD NOT RUN: no integration/ directory")
        return 2, lines
    # discover THIS tree's suite: a cached `integration` package from another tree would shadow it
    for name in [m for m in sys.modules if m == "integration" or m.startswith("integration.")]:
        del sys.modules[name]
    sys.path.insert(0, str(root))
    try:
        suite = unittest.TestLoader().discover(str(suite_dir), pattern=PATTERN, top_level_dir=str(root))
    finally:
        sys.path.remove(str(root))
    if suite.countTestCases() == 0:
        append_record(root, f"- {today} · {v} · integration tier: not verified in this environment (zero integration tests; {env})")
        lines.append("[integration] COULD NOT RUN: zero integration tests discovered — an empty tier is not a pass")
        return 2, lines
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    failed = len(result.failures) + len(result.errors)
    passed = result.testsRun - failed - len(result.skipped)
    lines.append(f"[integration] {passed} passed, {failed} failed, {len(result.skipped)} skipped")
    if failed or passed == 0:
        append_record(root, f"- {today} · {v} · integration tier: FAILED ({failed} failed, {passed} passed; environment: {env})")
        return 1, lines
    append_record(root, f"- {today} · {v} · integration tier: passed (environment: {env})")
    return 0, lines
