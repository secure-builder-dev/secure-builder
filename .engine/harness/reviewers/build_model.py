# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A construction session on local open-weight models — the build role (CW1), never the gate.

    python .engine/harness/reviewers/build_model.py --model devstral:24b-small-2505-q4_K_M --item N-2
    python .engine/harness/reviewers/build_model.py --phase tests --model gemma4:31b-it-q4_K_M --item N-2
    python harness/reviewers/build_model.py --task work/task.md --source harness/engine --tests harness/selftest \
        --test-cmd "python -m unittest selftest.test_gate" --test-cwd harness --model a,b

Two phases. `--phase tests` writes the acceptance tests for the item's definition of done
and succeeds only when they exist, parse, and fail against the current code. `--phase build`
(the default) refuses to start on a green suite and treats every test file that existed when
it started as read-only: construction makes the acceptance tests pass, never edits them.

The model answers with search/replace edits, not whole files: a 24B model rewriting a
400-line file loses lines; an edit whose search text is not found exactly once is refused
and the model is told why. After each round the test command runs; a round that leaves more
tests failing than the best state so far is rolled back. `--model` takes a comma-separated
list: after `--patience` rounds without improvement the next model takes over. Files are
written with LF line endings. Nothing is committed: the human reads the diff and commits,
and the gate is a different model in a different process. Loopback endpoint only.
"""
import argparse
import ast
import difflib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request

LOOPBACK = ("http://127.0.0.1", "http://localhost", "http://[::1]")
TEXT_EXT = (".py", ".html", ".htm", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".json", ".md", ".txt", ".toml", ".cfg", ".svg")  # TypeScript and React: the ticketer frontend
MAX_CONTEXT_FILE = 40_000
WHOLE_FILE = "<<WHOLE FILE>>"
WHOLE_FILE_MAX_LINES = 300
HINT_MAX = 1200      # larger files (vendored libraries, data) are listed by name, not shown
SCHEMA = {"type": "object", "properties": {
    "edits": {"type": "array", "items": {"type": "object", "properties": {
        "path": {"type": "string"}, "search": {"type": "string"}, "replace": {"type": "string"}},
        "required": ["path", "search", "replace"]}},
    "notes": {"type": "string"},
    "coverage": {"type": "array", "items": {"type": "object", "properties": {
        "clause": {"type": "integer"}, "test": {"type": "string"}}, "required": ["clause", "test"]}}},
    "required": ["edits", "notes"]}
EDIT_RULES = (
    "Answer ONLY with JSON: {\"edits\": [{\"path\", \"search\", \"replace\"}], \"notes\"}. Each edit replaces the exact text "
    "`search` in file `path` with `replace`. `search` must be copied character for character from the current file and must "
    "occur exactly once in it; include enough surrounding lines to make it unique. To create a new file give an empty "
    "`search` and the whole file as `replace`. To rewrite an existing file completely (to restructure it, or to delete a "
    "duplicated function), give `search` exactly <<WHOLE FILE>> and the complete new file as `replace`; use it for files "
    "under 300 lines. Paths are relative to the project root, with forward slashes.")


def read(p):
    p = pathlib.Path(p)
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def header(text):
    out = {}
    for line in text.splitlines():
        if not line.strip():
            break
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


VENDORED_DIRS = frozenset({"vendor", "vendored", "third_party", "third-party", "node_modules"})


def vendored(path):
    """Third-party code copied in byte-exact: never shown as editable, never written, never snapshotted."""
    return any(part in VENDORED_DIRS for part in path.split("/")[:-1])


def files_under(root, dirs):
    out = []
    for d in dirs:
        base = root / d
        if base.is_file():
            out.append(base)
            continue
        for p in sorted(base.rglob("*")) if base.is_dir() else []:
            if p.is_file() and p.suffix in TEXT_EXT and "__pycache__" not in p.parts and not vendored(p.relative_to(root).as_posix()):
                out.append(p)
    return out


def tree_text(root, dirs):
    parts, listed = [], []
    for p in files_under(root, dirs):
        rel = p.relative_to(root).as_posix()
        text = read(p)
        if len(text) > MAX_CONTEXT_FILE:
            listed.append(f"{rel} ({len(text)} chars, not shown)")
        else:
            parts.append(f"=== {rel} ===\n{text}")
    if listed:
        parts.append("Files present but not shown (too large to edit): " + ", ".join(listed))
    return "\n".join(parts) or "(no files yet)"


def split_clauses(done_when):
    """The clauses of a definition of done: its semicolon-separated parts, each one observable outcome."""
    # "every case has a test" is a rule about the tests, not an outcome a single test can express
    meta = re.compile(r"^(and\s+)?every\s+(case|clause|one)\s+(of\s+these\s+)?has\s+(a|its\s+own)\s+test\.?$", re.I)
    return [c.strip() for c in done_when.split(";") if c.strip() and not meta.match(c.strip())]


def test_names(root, dirs):
    """Every test function defined under the test directories."""
    names = set()
    for p in files_under(root, dirs):
        if p.suffix == ".py":
            names.update(re.findall(r"^\s*def (test_\w+)\s*\(", read(p), re.M))
        elif p.suffix in (".ts", ".tsx", ".js", ".jsx"):     # vitest/jest: it('name', ...) or test('name', ...)
            names.update(re.findall(r"(?<![\w.])(?:it|test)\(\s*['\"`]([^'\"`]+)['\"`]", read(p)))
    return names


def test_bodies(root, dirs):
    """{test function name: its source as the parser sees it} under the test directories. A reviewer note on the tests
    is acted on only when this changes: an edit to the imports alone is not a rewrite (ticketer TK-1a: two tests made
    the same call and expected different exceptions; the note said so, the model changed one import line, and the
    phase reported the tests written)."""
    bodies = {}
    for p in files_under(root, dirs):
        if p.suffix != ".py":
            continue
        try:
            tree = ast.parse(read(p))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                bodies[f"{p.name}:{node.name}"] = ast.dump(node)
    return bodies


def uncovered(clauses, covered, names):
    """Clause numbers (1-based) with no mapping to an existing test function (antipode A-4: five string
    checks were offered for an eight-clause definition of done and the phase reported success)."""
    return [i for i in range(1, len(clauses) + 1) if covered.get(i) not in names]


def static_hints(root, dirs):
    """Silent defects no test output names, found with the standard library's parser: a dict literal that
    repeats a constant key keeps only the last value (antipode A-4: a hard-coded Content-Security-Policy
    repeated in the headers dict overrode the computed one, the page's script was refused, and three models
    spent 24 rounds on a render test that said only '0 drawn')."""
    hints = []
    for p in files_under(root, dirs):
        if p.suffix != ".py":
            continue
        try:
            tree = ast.parse(read(p))
        except SyntaxError:
            continue
        for body in [tree.body] + [n.body for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            # a function or class defined twice at one level: only the last definition is ever used, so a fix to
            # the first is dead and every search for its body matches twice (daynight D-1: csp_for at lines 7 and 118)
            first = {}
            for d in body:
                if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if d.name in first:
                        hints.append(f"{p.relative_to(root).as_posix()}:{d.lineno}: {d.name} is defined again (first at line "
                                     f"{first[d.name]}); only this last definition is used — delete one of them")
                    first.setdefault(d.name, d.lineno)
        # the engine's CWE-400 scan rules, told to the model while it builds instead of at the gate (sitrep-relay,
        # outbox-dedupe, geofence-check and chunk-verify all passed their tests and were blocked by the scan for this)
        rel = p.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                    (b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", "")) in ("BaseHTTPRequestHandler", "SimpleHTTPRequestHandler")
                    for b in node.bases):
                sets_timeout = any(isinstance(s, (ast.Assign, ast.AnnAssign)) and any(
                    getattr(t, "id", None) == "timeout" for t in (s.targets if isinstance(s, ast.Assign) else [s.target]))
                    for s in node.body)
                if not sets_timeout:
                    hints.append(f"{rel}:{node.lineno}: request handler {node.name} sets no class attribute `timeout`: one silent "
                                 "client holds its connection for ever (CWE-400; the security scan blocks this). Add `timeout = 10` "
                                 "to the class — server.timeout does not do it")
            if isinstance(node, ast.Call) and (getattr(node.func, "id", None) == "HTTPServer"
                                               or getattr(node.func, "attr", None) == "HTTPServer"):
                hints.append(f"{rel}:{node.lineno}: HTTPServer serves one connection at a time (CWE-400; the security scan "
                             "blocks this): use http.server.ThreadingHTTPServer with daemon_threads = True")
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                seen = {}
                for k in node.keys:
                    if isinstance(k, ast.Constant):
                        if k.value in seen:
                            hints.append(f"{p.relative_to(root).as_posix()}:{k.lineno}: dict key {k.value!r} is repeated "
                                         f"(first at line {seen[k.value]}); only the last value is kept")
                        seen.setdefault(k.value, k.lineno)
    return hints


def occurrences(text, search):
    """Where `search` occurs: the line number of each match, so the model can add the context that tells them apart."""
    lines, starts, i = [], [], text.find(search)
    while i >= 0:
        starts.append(text.count("\n", 0, i) + 1)
        i = text.find(search, i + 1)
    for n in starts[:5]:
        lines.append(f"line {n}")
    return ", ".join(lines) + " — include lines around the one you mean (or remove the duplicate)"


def closest(text, search):
    """The passage of `text` most like `search` (same number of lines), quoted back so a model that
    misremembered a line can copy the real one; empty when nothing is close."""
    lines, want = text.split("\n"), search.strip("\n").split("\n")
    k = max(1, len(want))
    best, best_ratio = "", 0.0
    for i in range(0, max(1, len(lines) - k + 1)):
        window = "\n".join(lines[i:i + k])
        r = difflib.SequenceMatcher(None, window, "\n".join(want)).ratio()
        if r > best_ratio:
            best, best_ratio = window, r
    if best_ratio < 0.6:
        return ""
    # capped: a hint that quotes a whole class swells the next prompt (A-4 reached 65K characters)
    return best if len(best) <= HINT_MAX else best[:HINT_MAX] + "\n[... passage truncated]"


def apply_edits(root, edits, writable, readonly):
    """Apply search/replace edits. Returns (written paths, refusals). An edit is refused, and
    nothing of it written, when its path is outside the writable directories, is a read-only
    file, or its search text is not found exactly once. Line endings are normalized to LF."""
    written, refused, staged = [], [], {}
    for e in edits:
        rel = str(e.get("path", "")).replace("\\", "/").lstrip("./")
        search, replace = str(e.get("search", "")), str(e.get("replace", ""))
        if not rel or ".." in rel.split("/") or not any(rel == w.rstrip("/") or rel.startswith(w.rstrip("/") + "/") for w in writable):
            refused.append(f"{rel or '(no path)'}: outside the writable directories {list(writable)}")
            continue
        if vendored(rel):
            refused.append(f"{rel}: vendored third-party code is byte-exact and read-only — change the project's own files")
            continue
        if rel in readonly:
            refused.append(f"{rel}: an acceptance test that existed before construction; it is read-only — change the code, not the test")
            continue
        p = root / rel
        current = staged.get(rel, read(p).replace("\r\n", "\n") if p.is_file() else None)
        search, replace = search.replace("\r\n", "\n"), replace.replace("\r\n", "\n")
        if current is None or (not current.strip() and not search.strip()):
            # an empty existing file (a package's __init__.py) has no text to quote: writing it is a create
            # (daynight D-1: eight rounds refused because both models wrote into the empty tests/__init__.py)
            if search.strip():
                refused.append(f"{rel}: the file does not exist, so `search` must be empty to create it")
                continue
            new = replace
        elif search.strip() == WHOLE_FILE:
            # a whole-file rewrite: quoting 40 lines exactly to delete them is beyond a 24B model, rewriting a
            # 170-line file is not (daynight D-1: csp_for was defined twice and no model could remove one)
            if current.count("\n") > WHOLE_FILE_MAX_LINES:
                refused.append(f"{rel}: <<WHOLE FILE>> is for files under {WHOLE_FILE_MAX_LINES} lines; edit this one by search/replace")
                continue
            new = replace
        elif not search.strip():
            refused.append(f"{rel}: the file exists; give the exact text to replace in `search` (an empty search only creates new files)")
            continue
        else:
            n = current.count(search)
            if n != 1:
                stripped = [ln.rstrip() for ln in search.split("\n")]
                loose = "\n".join(stripped)
                cur_loose = "\n".join(ln.rstrip() for ln in current.split("\n"))
                if n == 0 and cur_loose.count(loose) == 1:
                    current, search = cur_loose, loose
                else:
                    hint = closest(current, search) if n == 0 else occurrences(current, search)
                    refused.append(f"{rel}: `search` occurs {n} times; it must occur exactly once — copy it exactly and add context"
                                   + ((f". The closest passage in the file is:\n{hint}" if n == 0 else f". It matches at {hint}") if hint else ""))
                    continue
            new = current.replace(search, replace, 1)
        if rel.endswith(".py"):
            # a copyright or notice line written as bare text is a comment the model forgot to mark
            # (daynight D-1: '© 2026 ...' as line 1 refused every round for eight rounds)
            first, sep, rest = new.partition("\n")
            if first.strip().startswith("©"):
                new = "# " + first.strip() + sep + rest
            try:
                compile(new, rel, "exec")
            except SyntaxError as err:
                refused.append(f"{rel}: the result does not parse — SyntaxError line {err.lineno}: {err.msg} -> {str(err.text or '').strip()[:100]}")
                continue
        staged[rel] = new
    for rel, new in staged.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new, encoding="utf-8", newline="\n")
        written.append(rel)
    return written, refused


def score(code, output):
    """Failing tests (failures + errors) from unittest output; 0 when the command passed.
    A suite that cannot even be collected scores worse than any count."""
    if code == 0:
        return 0
    m = re.search(r"FAILED \(([^)]*)\)", output)
    if m:
        n = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", m.group(1)))
        # a test module that cannot even be imported counts as one error but hides all its tests: score it as
        # uncollectable, so a round that makes it import (and shows 10 real failures) is progress, not a loss
        # (daynight D-1: fifteen rounds held at '1 failing' while the models' app.py never imported)
        if "unittest.loader._FailedTest" in output or re.search(r"^(ImportError|ModuleNotFoundError)\b", output, re.M):
            return 5_000 + n
        return n or 1
    # pytest and vitest (ticketer: a FastAPI backend and a React frontend run in one test command): every failure
    # counts, and a file that cannot be collected or imported hides its tests, so it scores as uncollectable
    n, seen, broken = 0, False, False
    for m in re.finditer(r"^=+ (.*?) in [\d.]+s(?: \([^)]*\))? =+$", output, re.M):           # pytest summary line
        seen = True
        n += sum(int(x) for x in re.findall(r"(\d+) (?:failed|errors?)", m.group(1)))
    for m in re.finditer(r"^\s*Tests\s+(.*)$", output, re.M):                                  # vitest summary line
        seen = True
        n += sum(int(x) for x in re.findall(r"(\d+) failed", m.group(1)))
    if re.search(r"errors? during collection|^ERROR collecting|^\s*Test Files\s+.*\d+ failed.*\(\d+\)\s*$(?![\s\S]*^\s*Tests\s)",
                 output, re.M) or re.search(r"Failed Suites \d+|Error: Failed to (?:load|resolve)", output):
        broken = True
    if seen or broken:
        return (5_000 if broken else 0) + (n or (0 if broken else 1))
    return 10_000


def runner_broken(code, output, root, sources, tests):
    """The test command crashed before any test framework ran, and the traceback names no file the model may edit:
    the runner itself is broken and no round can mend it (honey-do: a comment in the middle of a list in
    scripts/test_all.py was a SyntaxError for 32 rounds, each scored '10000 failing' and handed to the model)."""
    if code == 0 or score(code, output) != 10_000:
        return ""
    named = sorted({m.replace("\\", "/") for m in re.findall(r'File "([^"]+)"', output)})
    editable = {p.name for p in files_under(root, sources) + files_under(root, tests)}
    if any(n.rsplit("/", 1)[-1] in editable for n in named):
        return ""
    # a crash that names a source or test folder is the model's to mend: in the tests phase the tests folder may not
    # exist yet ("Start directory is not importable"), and the first round creates it
    flat = output.replace("\\\\", "/").replace("\\", "/")
    if any((root / d).resolve().as_posix() in flat or d.rstrip("/") in flat for d in sources + tests):
        return ""
    return ("the test command crashed before any test framework ran" +
            (f", in {', '.join(named)}" if named else "") + "; that is not a source or test file the model may edit, "
            "so no build round can fix it. Repair the test command (or the file it runs) and start again")


def first_error(output):
    """The first exception line of a test run, e.g. 'AssertionError: 404 != 200'; empty when there is none."""
    m = re.search(r"^\w*(?:Error|Exception):.*$", output, re.M)
    # numbers are dropped: a test server's port changes every run, and a changed port is not a changed error
    # (daynight D-1: every round read as "progress kept" because 127.0.0.1:<port> differed)
    return re.sub(r"\d+", "#", m.group(0))[:240] if m else ""


def failing_tests(output):
    """The names of the failing tests in unittest output ('test_x (module.Class.test_x)' -> 'module.Class.test_x')."""
    names = {m.group(2) or m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (\S+)(?: \(([^)]*)\))?", output, re.M)}
    # pytest short summary ('FAILED backend/tests/test_x.py::test_y - ...') and vitest ('FAIL  tests/a.test.tsx > App > y')
    names |= {m.group(1) for m in re.finditer(r"^(?:FAILED|ERROR) (\S+::\S+)", output, re.M)}
    names |= {m.group(1).strip() for m in re.finditer(r"^\s*FAIL\s+(\S+\.(?:test|spec)\.[jt]sx?\s+>.*?)\s*$", output, re.M)}
    return frozenset(names)


def snapshot(root, dirs):
    # bytes, not text: a restore must give back exactly what was there (antipode A-4: a text round trip
    # rewrote vendored Leaflet CSS with LF and broke its Subresource Integrity hash)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in files_under(root, dirs)}


def restore(root, snap, dirs):
    for p in files_under(root, dirs):
        rel = p.relative_to(root).as_posix()
        if rel not in snap:
            p.unlink()
    for rel, data in snap.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.is_file() or p.read_bytes() != data:
            p.write_bytes(data)


def ask(endpoint, model, system, user, num_ctx, temperature=0.1, think=False, require_coverage=False):
    # thinking is off unless asked for: a reasoning model's hidden thought is spent from the same output budget,
    # and Gemma 4 31B spent all of it on A-2 and answered nothing
    schema = dict(SCHEMA, required=SCHEMA["required"] + ["coverage"]) if require_coverage else SCHEMA
    body = {"model": model, "stream": False, "format": schema, "think": think,
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": 16384},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{endpoint}/api/chat", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        out = json.loads(r.read().decode("utf-8"))
    return json.loads(out["message"]["content"]), out


TEST_TIMEOUT = 600


def local_program(cmd, cwd):
    """The command with a project-relative program path made absolute: Windows does not resolve
    'backend/.venv/Scripts/python.exe' against the child's working directory (honey-do: every model phase died at once)."""
    cmd = [str(c) for c in cmd]
    if cmd and ("/" in cmd[0] or "\\" in cmd[0]) and not pathlib.Path(cmd[0]).is_absolute() and (pathlib.Path(cwd) / cmd[0]).exists():
        cmd[0] = str((pathlib.Path(cwd) / cmd[0]).resolve())
    return cmd


def run_tests(cmd, cwd, timeout=TEST_TIMEOUT):
    # a bounded run: a test that waits on a server that never answers (the CWE-400 fix's own acceptance test,
    # against the unfixed server) hung the suite, and the loop with it, for half an hour
    try:
        res = subprocess.run(local_program(cmd, cwd), cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = "".join(x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "") for x in (e.stdout, e.stderr))
        return 124, (out[-5000:] + f"\nFAIL: the test command did not finish within {timeout}s and was stopped. A test hung: "
                     "every network read or connection in a test needs its own timeout, so that a server that never "
                     "answers fails the test instead of blocking it. A test server's shutdown() waits for the request "
                     "it is handling: close every client socket the test opened (in a finally block or addCleanup) "
                     "before shutting the server down, or a failing test hangs in tearDown.\n")
    out = (res.stdout + res.stderr)[-6000:]
    nothing = suite_ran_nothing(res.stdout + res.stderr) if res.returncode == 0 else None
    if nothing:
        # an all-skipped suite is not a passing one: the round failed, and the model is told why
        return 1, out + (f"\nFAIL: {nothing}. A test that skips when the environment lacks a value must set that value "
                         "itself (setUp / setUpClass), never skip." + test_guidance(res.stdout + res.stderr))
    return res.returncode, out + test_guidance(res.stdout + res.stderr)


def suite_ran_nothing(output):
    """Why a passing exit code proves nothing, or None. A suite that ran no test, or skipped every test it found,
    exits 0 having checked nothing (nr-cot-builder: setUpClass skipped the class when APP_TOKEN was unset, and the
    tests phase and the gate both read 'OK' as passing)."""
    import re as _re
    ran = _re.findall(r"^Ran (\d+) tests? in", output, _re.M)
    if ran:
        n = int(ran[-1])
        skipped = _re.search(r"^OK \(skipped=(\d+)\)", output, _re.M)
        if n == 0:
            return "the suite ran no test (unittest: Ran 0 tests)"
        if skipped and int(skipped.group(1)) >= n:
            return f"every test was skipped ({skipped.group(1)} of {n}): a skipped test checks nothing"
        return None
    if _re.search(r"collected 0 items|no tests ran", output):
        return "the suite ran no test (pytest)"
    if _re.search(r"^=+ (\d+) skipped(?: in [\d.]+s)? =+$", output, _re.M):
        return "every test was skipped (pytest)"
    if _re.search(r"^\s*0 passing\b", output, _re.M):
        return "the suite ran no test (mocha: 0 passing)"
    return None


def start_check(serve_command, cwd, seconds=10):
    """Start the project as the gate's dynamic scan will (config serve_command) and report it when it dies on start.
    A test that only says "failed to start" hides the server's own error: nr-sensor-alert's settings.js crashed Node-RED
    for eight rounds and no model ever saw why; outbox-dedupe's server crashed on start the same way."""
    if not serve_command:
        return None
    import random
    import time
    port = random.randint(20000, 60000)
    cmd = local_program([str(c).replace("{port}", str(port)) for c in serve_command], cwd)
    env = dict(os.environ, PORT=str(port), APP_TOKEN=os.environ.get("APP_TOKEN") or "start-check-token")
    try:
        proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        return f"SERVER START CHECK: `{' '.join(cmd)}` could not be run ({e})"
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and proc.poll() is None:
        time.sleep(0.25)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return None
    out = (proc.stdout.read() if proc.stdout else "")[-2500:]
    return (f"SERVER START CHECK: `{' '.join(cmd)}` exited with code {proc.returncode} within {seconds}s instead of "
            f"serving; its own output:\n{out.strip() or '(nothing)'}")


def test_guidance(output):
    """Plain advice for the failures local models kept repeating, appended to what the model reads."""
    advice = []
    # geofence-check: `from src.server import ...` at module top; src/ did not exist yet, so no test ran for 8 rounds
    if "Failed to import test module" in output and re.search(r"No module named '?(src|app)\b", output):
        advice.append("A test module that imports the code under test at its top cannot load before that code exists, so "
                      "none of its tests run. Import the code under test inside setUp or setUpClass.")
    # sitrep-relay, nav-calc, outbox-dedupe: the request helper called e.headers() on urllib.error.HTTPError
    if "'HTTPMessage' object is not callable" in output:
        advice.append("urllib's response and HTTPError headers is an attribute, not a method: read dict(r.headers) or "
                      "dict(e.headers), never r.headers() or e.headers().")
    # sitrep-relay: the server thread's traceback said `no such table`, eight rounds never created it
    if re.search(r"sqlite3\.OperationalError: no such table", output):
        advice.append("The server thread reported `no such table`: the schema is never created. Create it (CREATE TABLE IF "
                      "NOT EXISTS) when the server is made, before it serves.")
    return "".join(f"\nENGINE NOTE: {a}" for a in advice)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="one model, or a comma-separated list tried in order")
    ap.add_argument("--item", help="the work item (tickets/<item>.md)")
    ap.add_argument("--task", help="a file stating the task, in place of an item (for work outside the project lifecycle)")
    ap.add_argument("--phase", choices=["build", "tests"], default="build")
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--num-ctx", type=int, default=24576)
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--patience", type=int, default=3, help="rounds without improvement before the next model takes over")
    ap.add_argument("--source", default="src", help="comma-separated writable source directories")
    ap.add_argument("--tests", default="tests", help="comma-separated test directories")
    ap.add_argument("--context", action="append", default=[], help="a read-only file or directory shown to the model")
    ap.add_argument("--test-cmd", help="the test command (default: the project's test_command)")
    ap.add_argument("--test-cwd", default=".")
    ap.add_argument("--root", default=".")
    ap.add_argument("--note", action="append", default=[], help="the human reviewer's note to the model (what the tests or code still miss)")
    ap.add_argument("--think", action="store_true", help="let a reasoning model think aloud (spent from the output budget)")
    a = ap.parse_args(argv)
    if not a.endpoint.startswith(LOOPBACK):
        print(f"build_model: REFUSED — endpoint {a.endpoint} is not the loopback interface")
        return 2
    root = pathlib.Path(a.root).resolve()
    if a.task:
        goal = read(root / a.task) or read(a.task)
        if not goal:
            print(f"build_model: COULD NOT RUN — task file {a.task} is empty or missing")
            return 2
        name = pathlib.Path(a.task).stem
        clauses = []
    else:
        if not a.item:
            print("build_model: COULD NOT RUN — give --item or --task")
            return 2
        ticket = read(root / "tickets" / f"{a.item}.md")
        if not ticket:
            print(f"build_model: COULD NOT RUN — no ticket tickets/{a.item}.md; create the item first (`item new`)")
            return 2
        h = header(ticket)
        # an open item is unowned: claim it first (A-2 was built while still open). An item in review is rework after
        # a blocked gate ("address the gate findings, then re-run the handoff"): refusing it left the ticketer gate unfixable
        if h.get("state") not in ("claimed", "in review"):
            print(f"build_model: REFUSED — item {a.item} is in state '{h.get('state')}'; construction happens on a claimed item, or one in review after a gate")
            return 2
        goal = f"Definition of done: {h.get('done_when', '(none)')}"
        clauses = split_clauses(h.get('done_when', ''))
        name = a.item
    try:
        cfg = json.loads(read(root / ".engine" / "rules" / "config.json"))
    except ValueError:
        cfg = {}
    sources = [s.strip().rstrip("/") for s in a.source.split(",") if s.strip()]
    tests = [t.strip().rstrip("/") for t in a.tests.split(",") if t.strip()]
    test_cmd = shlex.split(a.test_cmd) if a.test_cmd else (cfg.get("test_command") or [sys.executable, "-m", "unittest", "discover", "-s", tests[0], "-t", "."])
    test_cwd = (root / a.test_cwd).resolve()
    models = [m.strip() for m in a.model.split(",") if m.strip()]
    rules = read(root / ".engine" / "rules" / "RULES.md")
    if a.phase == "tests":
        writable, readonly = tests, set()
        role = ("You write acceptance tests. Express every clause of the definition of done as a unittest test that FAILS "
                "against the current code and will pass once the behaviour exists. Cover rejection cases (bad input, missing "
                "or wrong credentials where the design has credentials), not only success. Change only files under the test "
                "directories, in files named tests/test_<topic>.py (unittest discovers only test*.py; tests written into "
                "__init__.py never run).")
    else:
        writable = sources + tests
        readonly = {p.relative_to(root).as_posix() for p in files_under(root, tests)}
        role = ("You are the construction session. Make the failing tests pass by changing the source. The existing test "
                "files are the specification and are read-only; you may add new test files. Follow the design plan and the "
                "project rules exactly, including what the design says about credentials: a route the design declares public "
                "needs no credential check, every other route rejects a missing credential and, where a record belongs to a "
                "principal, another principal. Standard library only unless the plan names a dependency.")
    system = (role + " You never touch the harness, the records, the manifest, the plan or the tickets, and you never attribute "
              "yourself.\n\n" + EDIT_RULES + ("\n\n" + rules if rules else ""))
    code, output = run_tests(test_cmd, test_cwd)
    broken = runner_broken(code, output, root, sources, tests)
    if broken:
        print(f"build_model: COULD NOT RUN — {broken}")
        print(output[-1500:])
        return 2
    if a.phase == "build" and code == 0 and not a.note:
        # a green suite is not a definition of done: the model would rewrite what exists and be told it passed
        # (seen on the to-do demo: 120 tokens, the empty skeleton, "tests pass"). Construction starts red.
        print("build_model: REFUSED — the test suite already passes; write the failing acceptance tests that express "
              f"the definition of done first (`--phase tests`), then build")
        return 2
    if a.phase == "build" and code == 0:
        # a revision: the tests pass but a reviewer or the gate asked for a change (chunk-verify passed its tests and the
        # scan blocked it; with no way to hand that back the code could never be fixed by the models)
        print("build_model: revision — the suite passes; the reviewer's note is the change, and the suite must stay green")
    watched = sources + tests
    best_snap, best, best_failing = snapshot(root, watched), score(code, output), failing_tests(output)
    best_error = first_error(output)
    start_files = set(best_snap)
    start_bodies = test_bodies(root, tests)
    first_hints = static_hints(root, sources)
    feedback = (("STATIC CHECK OF THE SOURCE (no test reports these):" + chr(10) + chr(10).join(first_hints) + chr(10) * 2)
                if first_hints else "") + output
    temperature, stale, mi = 0.1, 0, 0
    covered = {}
    print(f"build_model: {a.phase} phase for {name}; models {models}; starting score {best} failing")
    for rnd in range(1, a.rounds + 1):
        model = models[mi]
        user = (f"Task {name}. {goal}\n\n"
                f"Design plan (plans/design.md):\n{read(root / 'plans' / 'design.md') or '(none)'}\n\n"
                f"Project rules (AGENTS.md):\n{read(root / 'AGENTS.md')[-3000:] or '(none)'}\n\n"
                + "".join(f"Read-only context ({c}):\n{tree_text(root, [c])}\n\n" for c in a.context)
                + f"Current files you may change (writable: {writable}):\n{tree_text(root, watched)}\n\n"
                f"Test command: {' '.join(test_cmd)} (run in {a.test_cwd})\n"
                + "".join(f"\nREVIEWER NOTE (from the human; act on it): {n}\n" for n in a.note)
                + (("\nTHE CLAUSES OF THE DEFINITION OF DONE (each needs its own test; answer `coverage` with one "
                    "{clause: <number>, test: <test function name>} per clause):\n"
                    + "".join(f"{i}. {c}\n" for i, c in enumerate(clauses, 1))) if a.phase == "tests" and clauses else "")
                + (f"\nCurrent test output:\n{feedback}\n" if feedback else ""))
        print(f"build_model: round {rnd} with {model}; prompt {len(user)} chars")
        # every prompt and answer is kept, so a human can tell a weak model from a weak instruction (ticketer)
        transcript = root / ".engine" / "work" / "prompts" / f"{name}-{a.phase}-round{rnd}.md"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text(f"# {name} {a.phase} round {rnd} — {model}, temperature {temperature:.2f}\n\n## System prompt\n\n"
                              f"{system}\n\n## User prompt\n\n{user}\n", encoding="utf-8", newline="\n")
        try:
            out, raw = ask(a.endpoint, model, system, user, a.num_ctx, temperature, a.think,
                           require_coverage=a.phase == "tests" and bool(clauses))
            with transcript.open("a", encoding="utf-8", newline="\n") as f:
                f.write("\n## Model answer\n\n```json\n" + json.dumps(out, indent=1)[:200_000] + "\n```\n")
        except urllib.error.URLError as e:
            if not isinstance(e, urllib.error.HTTPError):
                print(f"build_model: COULD NOT RUN — the model endpoint did not answer ({e})")
                return 2
            # an HTTP error from a live endpoint (ollama answered 500 on a 65K-character A-4 prompt) is a failed round
            print(f"build_model: round {rnd}: {model} failed on the server ({e})")
            stale = a.patience
            if mi + 1 < len(models):
                mi, stale, temperature = mi + 1, 0, 0.1
                print(f"build_model: handing over to {models[mi]}")
            continue
        except (OSError, ValueError, KeyError) as e:
            # an empty or malformed answer is a failed round, not the end of the run: the next model may do better
            print(f"build_model: round {rnd}: {model} gave no usable answer ({type(e).__name__}: {str(e)[:120]})")
            stale = a.patience
            if mi + 1 < len(models):
                mi, stale, temperature = mi + 1, 0, 0.1
                print(f"build_model: handing over to {models[mi]}")
            continue
        written, refused = apply_edits(root, out.get("edits") or [], writable, readonly)
        print(f"build_model: wrote {len(written)} file(s): {', '.join(written) or '-'}; refused {len(refused)}")
        print(f"build_model: model notes: {str(out.get('notes', ''))[:300]}")
        for r in refused:
            print(f"build_model: REFUSED edit {r}")
        code, output = run_tests(test_cmd, test_cwd)
        now, failing = score(code, output), failing_tests(output)
        print(f"build_model: test command exited {code}; {now} failing (best {best}); {raw.get('eval_count')} tokens in {raw.get('total_duration', 0) / 1e9:.0f}s"
              + (f"; failing: {', '.join(sorted(failing))}" if failing else ""))
        errors = re.findall(r"^\w*(?:Error|Exception):.*$", output, re.M)
        if errors:     # the human reading the log sees what the model saw (daynight D-1's log showed only counts)
            print(f"build_model: first error: {errors[0][:240]}")
        notes = ("EDITS REFUSED (nothing of these was written):\n" + "\n".join(refused) + "\n\n") if refused else ""
        hints = static_hints(root, sources)
        if a.phase == "build":
            crashed = start_check(cfg.get("serve_command"), root)
            if crashed:
                notes += crashed + "\n\n"
                print(f"build_model: start check: {crashed.splitlines()[0][:200]}")
        if hints:
            notes += "STATIC CHECK OF YOUR SOURCE (fix these first; no test reports them):\n" + "\n".join(hints) + "\n\n"
            if any("is defined again" in h for h in hints):
                notes += ("A duplicated definition is easiest to remove by rewriting the file whole: search <<WHOLE FILE>>, "
                          "replace with the complete file containing each function once.\n\n")
            print(f"build_model: static check: {len(hints)} problem(s): {hints[0]}")
        if a.phase == "tests":
            new_tests = set(snapshot(root, tests)) - start_files
            # every edit must land: a refused edit is a clause of the definition of done left unexpressed
            # (A-2: the CSP assertion edit was refused and the phase still reported success)
            for m in out.get("coverage") or []:
                try:
                    covered[int(m.get("clause"))] = str(m.get("test", "")).strip()
                except (TypeError, ValueError):
                    pass
            missing = uncovered(clauses, covered, test_names(root, tests))
            if missing:
                notes += ("CLAUSES WITH NO TEST (name an existing test function for each in `coverage`, writing the test "
                          "first if it does not exist):\n" + "\n".join(f"{i}. {clauses[i - 1]}" for i in missing) + "\n")
                print(f"build_model: {len(missing)} of {len(clauses)} clause(s) have no test yet: {missing}")
            unrevised = bool(a.note) and test_bodies(root, tests) == start_bodies
            if unrevised:
                notes += ("THE REVIEWER NOTE WAS NOT ACTED ON: no test function changed (an import edit is not a rewrite). "
                          "Change the tests the note names, and add the tests it asks for.\n")
                print("build_model: the reviewer note was not acted on: no test function changed")
            if written and not refused and not missing and not unrevised and code != 0 and now < 10_000:
                print(f"build_model: acceptance tests written and failing as they must ({now} failing; new files: {sorted(new_tests) or 'edits to existing files'}). "
                      "Read them before construction: they are the specification.")
                return 0
            if code == 0 and written:
                notes += "THE SUITE PASSES: the new tests do not fail against the current code, so they test nothing new. Make them assert the behaviour the definition of done requires.\n"
            if now >= 10_000:
                notes += "THE SUITE CANNOT BE COLLECTED (import or syntax error) — tests must import and run, then fail on assertions.\n"
            feedback = notes + output
            stale += 1
        else:
            blocking = [h for h in hints if "CWE-400" in h]
            if code == 0 and not refused and not blocking:
                print("build_model: tests pass. Nothing is committed: read the diff, commit as yourself, then scan, hand off and gate.")
                return 0
            if code == 0 and blocking:
                # green tests the security scan would still block are not done: keep this state and go round again
                print(f"build_model: tests pass, but {len(blocking)} defect(s) the security scan blocks remain; another round")
                best, best_snap, best_failing, best_error = 0, snapshot(root, watched), failing, first_error(output)
                stale += 1
                feedback = notes + output
            elif now < best:
                best, best_snap, best_failing, best_error, stale = now, snapshot(root, watched), failing, first_error(output), 0
                feedback = notes + output
            elif now == best and failing and (failing != best_failing or first_error(output) != best_error):
                # the same tests can fail for a new reason: a 404 that became a decode error means the code moved
                # (daynight D-1: static serving written in round 2 was discarded because the failing names matched)
                # as many failures, but different ones: the round moved (antipode A-4: a round that fixed the
                # country fill and broke the policy test tied 1-1 and was thrown away at the end of the run)
                notes += (f"PROGRESS KEPT: the same number of tests fail, but different ones ({', '.join(sorted(failing))} "
                          f"instead of {', '.join(sorted(best_failing))}). Your change is kept; now fix what it broke "
                          "without undoing what it fixed.\n")
                best_snap, best_failing, best_error = snapshot(root, watched), failing, first_error(output)
                stale += 1
                feedback = notes + output
            else:
                stale += 1
                if now > best:
                    restore(root, best_snap, watched)
                    notes += f"YOUR LAST EDITS MADE THINGS WORSE ({now} failing against {best}) AND WERE ROLLED BACK. The files above are not what you see now: the previous state is restored. Try a different approach.\n"
                    code, output = run_tests(test_cmd, test_cwd)
                feedback = notes + output
        if stale >= a.patience and mi + 1 < len(models):
            mi, stale, temperature = mi + 1, 0, 0.1
            print(f"build_model: no improvement in {a.patience} round(s); handing over to {models[mi]}")
        elif stale:
            temperature = min(0.6, temperature + 0.15)
    print(f"build_model: not converged after {a.rounds} round(s); best state kept ({best} failing) for the human to read")
    if a.phase == "build":
        restore(root, best_snap, watched)
    return 1


if __name__ == "__main__":
    sys.exit(main())
