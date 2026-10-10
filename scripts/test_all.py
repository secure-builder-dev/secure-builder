"""Run the whole suite: the FastAPI backend with pytest, then the React frontend with Vitest; each writes its coverage
report (backend/coverage.json, frontend/coverage/coverage-summary.json). Exits non-zero if either side fails.

Both runners' output goes to stdout in order, with their summary lines moved to the very end (moved, not copied,
so each failure is counted once). The build driver keeps only the tail of a long run, and Vitest writes its stack traces to stderr, after its stdout summary: TK-1c's
React traces pushed both summaries out of that tail, so a round that fixed App.tsx's parse error ('8 failed | 1 passed')
read as 'nothing ran' and was rolled back, 32 rounds in a row."""
import os
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # captured stdout is cp1252 on Windows; Vitest prints '❯'
ROOT = pathlib.Path(__file__).resolve().parent.parent
env = dict(os.environ, NO_COLOR="1", FORCE_COLOR="0")
env.setdefault("TICKETER_DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:55432/ticketer_test")
venv_python = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
SUMMARY = re.compile(r"^(?:=+ .*? in [\d.]+s(?: \([^)]*\))? =+|(?:FAILED|ERROR) \S+::\S+.*|.*errors? during collection.*"
                     r"|\s*(?:Test Files|Tests|Errors)\s+.*|.*Failed Suites \d+.*)$", re.M)


def run(cmd, cwd):
    # both commands are fixed lists built from this file's own location: no outside input reaches them
    # nosemgrep: dangerous-subprocess-use-audit
    r = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", errors="replace")
    sys.stdout.write(SUMMARY.sub("", r.stdout))
    sys.stdout.flush()
    return r.returncode, r.stdout


backend_rc, backend_out = run([str(venv_python), "-m", "pytest", "-rfE", "--cov=app", "--cov-report=json:coverage.json",
                               "--cov-report=term"], ROOT / "backend")
npx = "npx.cmd" if os.name == "nt" else "npx"
frontend_rc, frontend_out = run([npx, "vitest", "run", "--coverage"], ROOT / "frontend")
print("\n==== suite summary ====")
print(f"backend (pytest) exit {backend_rc}")
print("\n".join(m.group(0) for m in SUMMARY.finditer(backend_out)) or "(no pytest summary line)")
print(f"frontend (vitest) exit {frontend_rc}")
print("\n".join(m.group(0) for m in SUMMARY.finditer(frontend_out)) or "(no vitest summary line)")
sys.exit(1 if backend_rc or frontend_rc else 0)
