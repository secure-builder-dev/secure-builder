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

from . import layout

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
    for marker in ("/src/", "/lib/", "/app/", "/harness/engine/", "/engine/"):
        if marker in path and not path.startswith(("src/", "lib/", "app/", "harness/", "engine/")):
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
        text = pathlib.Path(path).read_text(encoding="utf-8")
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    # `# pragma: no cover` (coverage.py's convention) on a def excludes the whole function, on a statement that line:
    # only for code no line tracer can see, such as the trace callbacks below
    marked = {i for i, line in enumerate(text.splitlines(), 1) if "pragma: no cover" in line}
    excluded = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno in marked:
            excluded.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    # a docstring is a constant expression the interpreter never reports as a line run: counted, every documented
    # function read as partly uncovered however thoroughly it was tested
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstrings.add(first.lineno)
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            lines.add(node.lineno)
    return lines - excluded - marked - docstrings


class Collector:
    def __init__(self, root, prefix):
        self.root = pathlib.Path(root).resolve()
        self.prefix = str(self.root / prefix)
        self.hit = {}

    def _trace(self, frame, event, arg):  # pragma: no cover - a trace callback is never itself traced
        if event == "call":
            f = frame.f_code.co_filename
            if f.startswith(self.prefix):
                return self._line
            return None
        return None

    def _line(self, frame, event, arg):  # pragma: no cover - likewise
        if event == "line":
            self.hit.setdefault(frame.f_code.co_filename, set()).add(frame.f_lineno)
        return self._line

    def start(self):
        # threads started under the collector are traced too: a handler that runs in a server
        # thread (http.server under test) is exercised code, and unmeasured is not the same as uncovered
        self._previous = (sys.gettrace(), threading.gettrace())
        sys.settrace(self._trace)
        threading.settrace(self._trace)

    def stop(self):
        # restore, never clear: a collection nested inside another (the collector's own self-test runs one) used to
        # switch the outer tracer off, and every module tested after it read as uncovered (runner.py at 4.8%)
        prev_sys, prev_threads = getattr(self, "_previous", (None, None))
        sys.settrace(prev_sys)
        threading.settrace(prev_threads)

    def report(self):
        files = {}
        for p in sorted(pathlib.Path(self.prefix).rglob("*.py")):
            rel = p.relative_to(self.root).as_posix()
            if "dist" in p.parts or TEST_PATH.search(rel):     # test code is what measures, not what is measured
                continue
            total = executable_lines(p)
            covered = total & self.hit.get(str(p), set())
            files[rel] = {"covered": len(covered), "total": len(total)}
        return {"files": files}


def collect(root, run_suite, prefix=None, out=".engine/work/coverage.json"):
    """Run `run_suite()` under the collector and write the report. Returns the report. With no
    prefix, the whole harness is measured wherever the tree keeps it: the engine package and the build driver and
    reviewers beside it (a change to reviewers/build_model.py read as unmeasured when only the package was traced)."""
    if prefix is None:
        h = layout.harness_dir(root)
        prefix = layout.rel(root, h) if h else "engine"
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
