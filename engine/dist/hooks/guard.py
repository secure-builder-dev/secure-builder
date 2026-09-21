# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Pre-execution guard for a project. Two uses:

  python .engine/harness/hooks/guard.py check "git push origin main"
      exit 1 with the reason when the command is one of the three refused ones;
      wire this into the agent runtime's pre-execution hook.
  python .engine/harness/hooks/guard.py pre-push <remote> <url>   (git pre-push hook; reads refs on stdin)
      refuses a push that would update the protected branch.

Blocks exactly: push to the protected branch, merge while on it, remote merge.
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent        # .engine/harness/hooks
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / ".engine" / "harness"))
from engine import guard  # noqa: E402


def protected():
    try:
        return json.loads((ROOT / ".engine" / "rules" / "config.json").read_text(encoding="utf-8")).get("protected_branch", "main")
    except (OSError, ValueError):
        return "main"


def current():
    res = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    return res.stdout.strip()


def main(argv):
    if len(argv) >= 2 and argv[0] == "check":
        why = guard.blocks(argv[1], protected(), current())
        if why:
            print(f"guard: REFUSED — {why}. The protected branch is updated by a human merge only.")
            return 1
        return 0
    if argv and argv[0] == "pre-push":
        branch = protected()
        for line in sys.stdin.read().splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2].endswith(f"/{branch}"):
                print(f"guard: REFUSED — push would update protected branch '{branch}'")
                return 1
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
