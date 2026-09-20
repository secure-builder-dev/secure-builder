# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Project pre-commit hook: the credential scan against the staged index, using
the same definition of a credential as the routine check (spec 01 REQ-10.3).
Install: copy or symlink to .git/hooks/pre-commit, or invoke from it."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
res = subprocess.run([sys.executable, str(ROOT / ".engine" / "harness" / "run.py"), "credential-scan", "--staged"])
sys.exit(res.returncode)
