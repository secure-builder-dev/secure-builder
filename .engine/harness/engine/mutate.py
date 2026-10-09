# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Mutation of declared controls (spec 01 §5.3, REQ-7.4.2).

A passing test proves the code behaves; it does not prove the test would notice
if the code stopped behaving. Before the gate can pass, every declared control
is broken on purpose, the project's suite is run, and the suite must fail. A
baseline run comes first — mutation against an already-failing suite means
nothing. The mutation fits the control's shape, each enforcement branch is
mutated independently, and every mutated file is restored and the restoration
verified rather than assumed. Results are appended to the mutation-results
record.
"""
import pathlib
import re

from . import gitutil, tools
from .records import now, table
from .records import schema as sch

RESULTS = ".engine/records/mutation-results.md"
SHAPES = ("middleware", "decision", "scoping", "redaction", "other")


def infer_shape(symbol, signature):
    s = symbol.lower()
    if re.search(r"\bnext\b", signature) or re.search(r"middleware|guard|interceptor|handler_chain", s):
        return "middleware"
    if re.match(r"(can|is|has|may|allow|permit|check|authori[sz]e|validate|verify)_?", s):
        return "decision"
    if re.search(r"scope|filter|tenant|owner|for_user|visible", s):
        return "scoping"
    if re.search(r"redact|sanitiz|mask|scrub|anonymi", s):
        return "redaction"
    return "other"


def _params(signature):
    m = re.search(r"\((.*?)\)", signature, re.S)
    if not m:
        return []
    out = []
    for p in m.group(1).split(","):
        p = p.strip().split("=")[0].split(":")[0].strip().lstrip("*")
        if p and p not in ("self", "cls"):
            out.append(p)
    return out


def injected_statement(shape, params, language):
    """The statement that breaks the property, by shape (spec 01 REQ-5.3.2)."""
    first = params[0] if params else None
    nxt = next((p for p in params if p == "next"), None)
    if shape == "middleware":
        if language == "py":
            return f"return {nxt}({', '.join(p for p in params if p != 'next')})" if nxt else "return None"
        return f"return {nxt}();" if nxt else "return;"
    if shape == "decision":
        return "return True" if language == "py" else "return true;"
    if shape in ("scoping", "redaction"):
        if first is None:
            return "return None" if language == "py" else "return;"
        return f"return {first}" if language == "py" else f"return {first};"
    return "return None" if language == "py" else "return;"


def _language(path):
    return {"py": "py", "js": "js", "jsx": "js", "ts": "js", "tsx": "js", "mjs": "js", "cjs": "js"}.get(pathlib.Path(path).suffix.lstrip("."))


def mutate_source(text, symbol, shape_override=None):
    """Return (mutated text, description) for the shape-appropriate mutation of `symbol`,
    or (None, reason) when the language or definition is unsupported."""
    lines = text.splitlines(keepends=True)
    py = re.compile(r"^(\s*)(?:async\s+)?def\s+" + re.escape(symbol) + r"\s*\(")
    js = re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?(?:function\s+" + re.escape(symbol) + r"\s*\(|(?:const|let|var)\s+" + re.escape(symbol) + r"\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>|" + re.escape(symbol) + r"\s*\([^)]*\)\s*\{)")
    for i, line in enumerate(lines):
        m = py.match(line)
        if m:
            j = i
            sig = line
            while ":" not in sig.split(")")[-1] and j + 1 < len(lines):
                j += 1
                sig += lines[j]
            params = _params(sig)
            shape = shape_override or infer_shape(symbol, sig)
            stmt = injected_statement(shape, params, "py")
            body_indent = m.group(1) + "    "
            k = j + 1
            if k < len(lines) and re.match(r'^\s*[rbu]*("""|\'\'\')', lines[k]):   # skip a docstring
                q = re.match(r'^\s*[rbu]*("""|\'\'\')', lines[k]).group(1)
                if lines[k].count(q) < 2:
                    k += 1
                    while k < len(lines) and q not in lines[k]:
                        k += 1
                k += 1
            lines.insert(k, f"{body_indent}{stmt}  # engine:mutation\n")
            return "".join(lines), f"{shape}: injected `{stmt}` as the first statement of {symbol}"
        m = js.match(line)
        if m:
            j = i
            sig = line
            while "{" not in sig and j + 1 < len(lines):
                j += 1
                sig += lines[j]
            params = _params(sig)
            shape = shape_override or infer_shape(symbol, sig)
            stmt = injected_statement(shape, params, "js")
            brace = sig.rfind("{")
            before, after = sig[:brace + 1], sig[brace + 1:]
            replaced = before + f" {stmt} /* engine:mutation */" + after
            lines[i:j + 1] = [replaced]
            return "".join(lines), f"{shape}: injected `{stmt}` as the first statement of {symbol}"
    return None, f"no supported definition of {symbol} found (Python and JavaScript/TypeScript functions are supported; declare an explicit mutation override)"


def apply_edits(text, edits):
    for e in edits:
        if text.count(e["find"]) != 1:
            return None, f"explicit edit must match exactly once: {e['find']!r}"
        text = text.replace(e["find"], e["replace"])
    return text, f"explicit edits ({len(edits)})"


def plan(control):
    """The mutations to apply for one control: [(branch name, override-or-None)]."""
    branches = control.get("branches")
    if branches:
        return [(b["name"], b) for b in branches]
    return [("-", control.get("mutation"))]


def run(root, cfg, controls, test_command=None, runner=None):
    """Mutate every control (and every branch), run the suite, restore. Returns a
    summary dict; appends one mutation-results row per mutation."""
    root = pathlib.Path(root)
    test_command = test_command or (cfg.get("test_command") if cfg else None)
    if not test_command:
        return {"state": "could-not-run", "reason": "no test_command configured; the project's suite cannot be run"}
    runner = runner or (lambda: _run_tests(root, test_command))
    base = runner()
    if base != 0:
        return {"state": "red-baseline", "reason": f"baseline suite exited {base}; mutation results against a failing suite mean nothing"}
    results = []
    for c in controls:
        loc = c["location"]
        path = root / loc["file"]
        if not path.is_file():
            results.append(_result(c, "-", "could-not-mutate", f"{loc['file']} does not exist"))
            continue
        original = path.read_bytes()
        for branch, override in plan(c):
            text = original.decode("utf-8", errors="replace")
            if override and override.get("edits"):
                mutated, desc = apply_edits(text, override["edits"])
            else:
                mutated, desc = mutate_source(text, loc["symbol"], (override or {}).get("shape"))
            if mutated is None:
                results.append(_result(c, branch, "could-not-mutate", desc))
                continue
            try:
                path.write_bytes(mutated.encode("utf-8"))
                rc = runner()
            finally:
                path.write_bytes(original)
            if path.read_bytes() != original:
                results.append(_result(c, branch, "restore-failed", desc))
                continue
            verdict = "suite-failed" if rc != 0 else "suite-stayed-green"
            results.append(_result(c, branch, verdict, desc))
    for r in results:
        _record(root, cfg, r)
    bad = [r for r in results if r["verdict"] != "suite-failed"]
    return {"state": "failed" if bad else "passed", "results": results, "baseline": base}


def _result(c, branch, verdict, desc):
    return {"control": c["id"], "branch": branch, "verdict": verdict, "mutation": desc}


def _record(root, cfg, r):
    p = pathlib.Path(root) / RESULTS
    if not p.is_file():
        return
    table.append(root, RESULTS, sch.MUTATION, {
        "date": now(cfg), "control": r["control"], "branch": r["branch"], "mutation": r["mutation"],
        "baseline": "green", "result": r["verdict"], "side": cfg.side if cfg else sch.UNKNOWN})


def _run_tests(root, cmd):
    res = tools.run_tool(cmd[0], cmd[1:], cwd=str(root))
    return res.exit_code if res.ran else 127


def read_results(root):
    rows, problems, _ = table.read(root, RESULTS, "mutation-results")
    return rows or [], problems
