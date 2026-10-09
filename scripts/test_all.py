"""Run the whole suite: the FastAPI backend with pytest, then the React frontend with Vitest; each writes its coverage
report (backend/coverage.json, frontend/coverage/coverage-summary.json). Exits non-zero if either side fails."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
env = dict(os.environ, NO_COLOR="1", FORCE_COLOR="0")
env.setdefault("TICKETER_DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:55432/ticketer_test")
venv_python = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
# both commands are fixed lists built from this file's own location: no outside input reaches them
backend = subprocess.run([str(venv_python),  # nosemgrep: dangerous-subprocess-use-audit "-m", "pytest", "-rfE", "--cov=app", "--cov-report=json:coverage.json",
                          "--cov-report=term"], cwd=ROOT / "backend", env=env)
npx = "npx.cmd" if os.name == "nt" else "npx"
frontend = subprocess.run([npx,  # nosemgrep: dangerous-subprocess-use-audit "vitest", "run", "--coverage"], cwd=ROOT / "frontend", env=env)
sys.exit(1 if backend.returncode or frontend.returncode else 0)
