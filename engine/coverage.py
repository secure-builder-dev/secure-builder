# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Coverage measurement and range-scoped evaluation (spec 01 §5.1).

Thresholds are evaluated against the files changed in the range under review,
never the project average: a large well-tested codebase must not absorb an
untested new control without moving the number. Thresholds vary by layer, with
the highest where controls live.

Reports are read from the project's own tool in one of three shapes — an
istanbul `coverage-summary.json`, a coverage.py JSON report, or this module's
own `{"files": {path: {"covered": n, "total": m}}}`. For the harness itself,
`collect` measures the self-test suite with the standard library alone.
"""
import ast
import json
import pathlib
import re
import sys
import threading

SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".kt", ".java", ".go", ".rb", ".rs"}
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__|selftest|fixtures?)/|[._-]test\.|_test\.py$|\.spec\.")
DEFAULT_THRESHOLDS = {"default": 80, "layers": [
    {"pattern": r"(^|/)(services?|domain|middleware|auth|data|repositor(y|ies)|models?)/", "min": 90}]}


def read_report(path):
    """Return {relative path: percent covered} or None if unreadable."""
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    out = {}
    files = data.get("files") if isinstance(data, dict) else None
    if isinstance(files, dict):
        for f, v in files.items():
            if isinstance(v, dict) and "summary" in v:                       # coverage.py
                out[_norm(f)] = float(v["summary"].get("percent_covered", 0))
            elif isinstance(v, dict) and "total" in v:                      # this module's shape
                out[_norm(f)] = 100.0 * v["covered"] / v["total"] if v["total"] else 100.0
        return out
    if isinstance(data, dict):                                              # istanbul summary
        for f, v in data.items():
            if f == "total" or not isinstance(v, dict):
                continue
            lines = v.get("lines") or {}
            if "pct" in lines:
                out[_norm(f)] = float(lines["pct"])
        return out
    return None


def _norm(path):
    path = str(path).replace("\\", "/")
    for marker in ("/src/", "/lib/", "/app/", "/engine/"):
        if marker in path and not path.startswith(("src/", "lib/", "app/", "engine/")):
            i = path.rfind(marker)
            return path[i + 1:]
    return path.lstrip("./")


def threshold_for(path, thresholds):
    for layer in thresholds.get("layers", []):
        if re.search(layer["pattern"], path):
            return float(layer["min"])
    return float(thresholds.get("default", 80))


def evaluate(changed_files, report, thresholds):
    """Findings for changed source files below their layer's threshold or absent from the report."""
    findings, assessed = [], 0
    for f in changed_files:
        if pathlib.Path(f).suffix not in SOURCE_EXT or TEST_PATH.search(f):
            continue
        assessed += 1
        need = threshold_for(f, thresholds)
        pct = report.get(f)
        if pct is None:
            findings.append(f"{f}: changed in range but absent from the coverage report (needs {need:.0f}%)")
        elif pct < need:
            findings.append(f"{f}: {pct:.1f}% covered, threshold {need:.0f}% for its layer")
    return assessed, findings


# --- measuring the harness itself, standard library only ---

def executable_lines(path):
    try:
        tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            lines.add(node.lineno)
    return lines


class Collector:
    def __init__(self, root, prefix):
        self.root = pathlib.Path(root).resolve()
        self.prefix = str(self.root / prefix)
        self.hit = {}

    def _trace(self, frame, event, arg):
        if event == "call":
            f = frame.f_code.co_filename
            if f.startswith(self.prefix):
                return self._line
            return None
        return None

    def _line(self, frame, event, arg):
        if event == "line":
            self.hit.setdefault(frame.f_code.co_filename, set()).add(frame.f_lineno)
        return self._line

    def start(self):
        # threads started under the collector are traced too: a handler that runs in a server
        # thread (http.server under test) is exercised code, and unmeasured is not the same as uncovered
        sys.settrace(self._trace)
        threading.settrace(self._trace)

    def stop(self):
        sys.settrace(None)
        threading.settrace(None)

    def report(self):
        files = {}
        for p in sorted(pathlib.Path(self.prefix).rglob("*.py")):
            if "dist" in p.parts:
                continue
            total = executable_lines(p)
            covered = total & self.hit.get(str(p), set())
            files[p.relative_to(self.root).as_posix()] = {"covered": len(covered), "total": len(total)}
        return {"files": files}


def collect(root, run_suite, prefix="engine", out=".engine/local/coverage.json"):
    """Run `run_suite()` under the collector and write the report. Returns the report."""
    c = Collector(root, prefix)
    c.start()
    try:
        run_suite()
    finally:
        c.stop()
    rep = c.report()
    p = pathlib.Path(root) / out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return rep
