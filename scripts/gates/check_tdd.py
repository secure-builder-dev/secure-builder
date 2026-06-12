#!/usr/bin/env python3
"""check_tdd.py — TDD two-commit verification (Guarantee #3).

Verifies, for a story, that a test-only commit (`[S-XXX/tests] ...`) precedes the
implementation commit (`[S-XXX/impl] ...`) in git history — the machine-checkable core
of Guarantee #3. Absence of the prior failing-test commit is an automatic FAIL
regardless of any agent's assertion (PRD §5.1, CLAUDE.md §4.1).

What this PROVES: commit ordering and the naming convention. What it does NOT prove:
that the red-phase tests genuinely failed before impl, or that a test wasn't trivially
neutered (e.g. `expect(true).toBe(true)`). Those are heuristic/manual backstops
(PRD §4.4). Do not describe this as exhaustive.

Stdlib only.

Usage:
    check_tdd.py --story S-001                 # scan history for the pair
    check_tdd.py --story S-001 --range main..HEAD
    check_tdd.py --staged-msg "<msg>"          # pre-commit: validate the message prefix

Exit codes: 0 = compliant, 1 = violation, 2 = usage error.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_RE = lambda s: re.compile(rf"^\[{re.escape(s)}/tests\]")
IMPL_RE = lambda s: re.compile(rf"^\[{re.escape(s)}/impl\]")
PREFIX_RE = re.compile(r"^\[(?:[SF]-[A-Za-z0-9]+/(?:tests|impl)|[SF]-[A-Za-z0-9]+/[a-z]+)\]")


def git_log(extra):
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--format=%H%x09%s", *extra],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"error: git failed: {out.stderr.strip()}")
    rows = []
    for line in out.stdout.splitlines():
        if "\t" in line:
            h, s = line.split("\t", 1)
            rows.append((h, s))
    return rows  # newest first


def check_story(story, rng):
    extra = [rng] if rng else []
    rows = list(reversed(git_log(extra)))  # oldest first
    tests_idx = impl_idx = None
    t_re, i_re = TESTS_RE(story), IMPL_RE(story)
    for i, (h, s) in enumerate(rows):
        if tests_idx is None and t_re.match(s):
            tests_idx = i
        if i_re.match(s):
            impl_idx = i  # last impl commit for the story
    print(f"TDD check — story: {story}")
    if impl_idx is None:
        print("  no impl commit found for this story — nothing to verify yet (PASS/N-A).")
        return 0
    if tests_idx is None:
        print(f"  FAIL: impl commit present but NO preceding `[{story}/tests]` commit.")
        print("  → Guarantee #3 violation. Automatic TDD FAIL.")
        return 1
    if tests_idx < impl_idx:
        print(f"  PASS: `[{story}/tests]` (#{tests_idx}) precedes `[{story}/impl]` (#{impl_idx}).")
        return 0
    print(f"  FAIL: `[{story}/tests]` does not precede `[{story}/impl]` in history.")
    return 1


def check_msg(msg):
    first = msg.strip().splitlines()[0] if msg.strip() else ""
    print(f"Commit-message prefix check: {first!r}")
    if PREFIX_RE.match(first):
        print("  OK: recognized [S-XXX/tests|impl] or [F-XXX/...] prefix.")
        return 0
    print("  FAIL: message must start with [S-XXX/tests], [S-XXX/impl], or [F-XXX/...].")
    print("  (Non-story chores may use [F-XXX/...]; see CLAUDE.md §7.)")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", help="story id, e.g. S-001")
    ap.add_argument("--range", help="git commit range to scan")
    ap.add_argument("--staged-msg", help="commit message to validate the prefix of")
    a = ap.parse_args()
    if a.staged_msg is not None:
        return check_msg(a.staged_msg)
    if a.story:
        return check_story(a.story, a.range)
    ap.error("one of --story or --staged-msg is required")


if __name__ == "__main__":
    sys.exit(main())
