# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Project pre-commit hook: the credential scan against the staged index with the
same definition as the routine check (spec 01 REQ-10.3), and the governance rule
that a staged change to the rule set has its changelog row already written (spec
01 REQ-11.8.2). Install: copy or symlink to .git/hooks/pre-commit, or invoke from it."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / ".engine" / "harness"))
from engine import config as cfgmod, governance  # noqa: E402

res = subprocess.run([sys.executable, str(ROOT / ".engine" / "harness" / "run.py"), "credential-scan", "--staged"])
code = res.returncode
try:
    cfg = cfgmod.load(ROOT)
except cfgmod.ConfigError:
    cfg = None
for p in governance.staged_problems(ROOT, cfg):
    print(f"pre-commit: governance: {p}")
    code = 1
sys.exit(code)
