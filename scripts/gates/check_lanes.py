#!/usr/bin/env python3
"""check_lanes.py — Lane-boundary enforcement (Guarantee #5, file-ownership dimension).

Diffs the files touched in a commit range against the acting agent's owned-artifact
globs (agents/manifest.json) and flags anything outside that lane.

This is the MACHINE-CHECKABLE half of Guarantee #5 only. The SEMANTIC half — a
decision buried inside an allowed file (e.g. a developer making an architectural
choice inside an allowed src/ file) — is NOT detectable here and remains human/Sentinel
judgment (CLAUDE.md §2.2, PRD §3.2). A clean run here is necessary, not sufficient.

Stdlib only — no third-party deps (air-gap friendly).

Usage:
    check_lanes.py --agent Forge --range <base>..<head>
    check_lanes.py --agent Forge --staged          # check staged changes
    check_lanes.py --list-agents

Exit codes: 0 = in-lane (or no touched files), 1 = out-of-lane finding(s), 2 = usage/config
error. 1 and 2 are kept distinct on purpose: a hook must be able to tell a real lane
FINDING from a broken invocation. Never collapse them.
"""
import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

# Gate output is evidence and is read on Windows consoles (cp1252) as well as POSIX.
# Without this, a non-ASCII character in a FINDING line raises UnicodeEncodeError and
# the operator sees a traceback instead of the finding. Stdlib only.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # already-wrapped or non-reconfigurable stream
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "agents" / "manifest.json"


def die(msg):
    """Usage/config failure — exit 2, never 1 (1 means a genuine lane finding)."""
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def load_manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))["agents"]
    except FileNotFoundError:
        die(f"manifest not found at {MANIFEST}")
    except (json.JSONDecodeError, KeyError) as e:
        die(f"malformed manifest {MANIFEST}: {e}")


def git_files(args):
    """Return repo-relative, forward-slash paths touched by the given git selector."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        die(f"git failed: {out.stderr.strip()}")
    return [line.replace("\\", "/") for line in out.stdout.splitlines() if line.strip()]


def matches_any(path, globs):
    """gitignore-ish: a `dir/**` glob also matches the directory's descendants.

    fnmatchcase — NOT fnmatch — is deliberate. fnmatch applies os.path.normcase, which
    is case-insensitive on Windows and case-sensitive on POSIX; the same commit would
    then get different lane verdicts on the dev laptop and the air-gapped Linux target.
    A gate that produces evidence must be platform-deterministic.
    """
    for g in globs:
        if fnmatch.fnmatchcase(path, g):
            return True
        if g.endswith("/**") and (path == g[:-3] or path.startswith(g[:-2])):
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", help="acting agent (persona name from the manifest)")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--range", help="git commit range, e.g. main..HEAD")
    src.add_argument("--staged", action="store_true", help="check staged (index) changes")
    ap.add_argument("--list-agents", action="store_true", help="print known agents and exit")
    a = ap.parse_args()

    agents = load_manifest()

    if a.list_agents:
        for name, spec in agents.items():
            print(f"{name:10s} — {spec['lane']}")
        return 0

    if not a.agent:
        ap.error("--agent is required (or use --list-agents)")
    if a.agent not in agents:
        die(f"unknown agent '{a.agent}'. Known: {', '.join(agents)}")

    if a.staged:
        touched = git_files(["diff", "--cached", "--name-only"])
    elif a.range:
        touched = git_files(["diff", "--name-only", a.range])
    else:
        ap.error("one of --range or --staged is required")

    globs = agents[a.agent].get("owned_globs", [])
    out_of_lane = [p for p in touched if not matches_any(p, globs)]

    print(f"Lane check — agent: {a.agent}  ({len(touched)} file(s) touched)")
    if not touched:
        print("  no files touched — nothing to check.")
        return 0
    if not out_of_lane:
        print(f"  IN-LANE: all touched files within {a.agent}'s owned globs.")
        return 0

    print(f"  OUT-OF-LANE FINDING(S) — {len(out_of_lane)} file(s) outside {a.agent}'s lane:")
    for p in out_of_lane:
        print(f"    - {p}")
    print("  → Lane-boundary finding (OWASP LLM08). Reassign the work to the owning agent,")
    print("    or record an accepted exception in the gate log. Owned globs:")
    for g in globs:
        print(f"      {g}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
