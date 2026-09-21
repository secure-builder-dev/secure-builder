# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A construction session on a local open-weight model — the build role (CW1), never the gate.

    python .engine/reviewers/build_model.py --model devstral:24b-small-2505-q4_K_M --item N-2

The model is given the work item's definition of done, the design plan, the project
rules, and the current source and tests, and asked for the files to write. It may
write only under the source and test directories — never the harness, the records,
the governed files, the plan or the tickets. After each pass the project's own test
command runs; failures go back to the model for up to a few rounds. Nothing is
committed: the human reads the diff and commits, and the gate is a different model
in a different process. Loopback endpoint only.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

LOOPBACK = ("http://127.0.0.1", "http://localhost", "http://[::1]")
SCHEMA = {"type": "object", "properties": {
    "files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                                          "required": ["path", "content"]}},
    "notes": {"type": "string"}}, "required": ["files", "notes"]}


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


def tree_text(root, dirs):
    parts = []
    for d in dirs:
        for p in sorted((root / d).rglob("*")):
            if p.is_file() and p.suffix == ".py" and "__pycache__" not in p.parts:
                parts.append(f"=== {p.relative_to(root).as_posix()} ===\n{read(p)}")
    return "\n".join(parts) or "(no source yet)"


def ask(endpoint, model, system, user, num_ctx, temperature=0.1):
    body = {"model": model, "stream": False, "format": SCHEMA, "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{endpoint}/api/chat", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        out = json.loads(r.read().decode("utf-8"))
    return json.loads(out["message"]["content"]), out


def run_tests(root, cmd):
    res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, (res.stdout + res.stderr)[-6000:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--source", default="src")
    ap.add_argument("--tests", default="tests")
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)
    if not a.endpoint.startswith(LOOPBACK):
        print(f"build_model: REFUSED — endpoint {a.endpoint} is not the loopback interface")
        return 2
    root = pathlib.Path(a.root).resolve()
    ticket = read(root / "tickets" / f"{a.item}.md")
    if not ticket:
        print(f"build_model: COULD NOT RUN — no ticket tickets/{a.item}.md; create the item first (`item new`)")
        return 2
    h = header(ticket)
    if h.get("state") not in ("claimed", "open"):
        print(f"build_model: REFUSED — item {a.item} is in state '{h.get('state')}'; construction happens on a claimed item")
        return 2
    try:
        cfg = json.loads(read(root / ".engine" / "config.json"))
    except ValueError:
        cfg = {}
    test_cmd = cfg.get("test_command") or [sys.executable, "-m", "unittest", "discover", "-s", a.tests, "-t", "."]
    allowed = (a.source.rstrip("/") + "/", a.tests.rstrip("/") + "/")
    rules = read(root / ".engine" / "rules" / "RULES.md")
    system = ("You are the construction session for a software project governed by the rules below. You write code and tests "
              "only; you never touch the harness, the records, the manifest, the plan or the tickets, and you never attribute "
              "yourself. Every route must reject a missing credential and, where a record belongs to a principal, another "
              "principal. Tests must cover the rejection cases, not only success. Answer only with the JSON the schema describes: "
              "the complete content of each file you create or change.\n\n" + rules)
    code, output = run_tests(root, test_cmd)
    if code == 0:
        # a green suite is not a definition of done: the model would rewrite what exists and be told it passed
        # (seen on the to-do demo: 120 tokens, the empty skeleton, "tests pass"). Construction starts red.
        print("build_model: REFUSED — the test suite already passes; write the failing acceptance tests that express "
              f"the definition of done under {a.tests}/ first, then build (a run that changes nothing would 'converge')")
        return 2
    feedback = output
    last_written = {}
    temperature = 0.1
    for rnd in range(1, a.rounds + 1):
        user = (f"Work item {a.item}. Definition of done: {h.get('done_when', '(none)')}\n\n"
                f"Design plan (plans/design.md):\n{read(root / 'plans' / 'design.md') or '(none)'}\n\n"
                f"Project rules (AGENTS.md):\n{read(root / 'AGENTS.md')[-3000:]}\n\n"
                f"Current source and tests:\n{tree_text(root, [a.source, a.tests])}\n\n"
                f"Standard library only. Write files under {a.source}/ and {a.tests}/ only; give each file's full content.\n"
                + (f"\nThe test suite currently FAILS; make it pass:\n{feedback}\n" if feedback else ""))
        print(f"build_model: round {rnd} with {a.model}; prompt {len(user)} chars")
        try:
            out, raw = ask(a.endpoint, a.model, system, user, a.num_ctx, temperature)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f"build_model: COULD NOT RUN — the model did not answer ({e})")
            return 2
        written, refused, rejected, now = [], [], [], {}
        for f in out.get("files") or []:
            rel = str(f.get("path", "")).replace("\\", "/").lstrip("./")
            if not rel.startswith(allowed) or ".." in rel.split("/"):
                refused.append(rel)
                continue
            p = root / rel
            content = str(f.get("content", ""))
            if rel.endswith(".py"):
                try:
                    compile(content, rel, "exec")
                except SyntaxError as e:
                    # a file that does not parse is not written: the healthy version stays and the model is told exactly why
                    rejected.append(f"{rel}: SyntaxError line {e.lineno}: {e.msg} -> {str(e.text or '').strip()[:100]}")
                    continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8", newline="\n")
            written.append(rel)
            now[rel] = content
        identical = bool(now) and all(last_written.get(k) == v for k, v in now.items())
        last_written.update(now)
        print(f"build_model: wrote {len(written)} file(s): {', '.join(written)}" + (f"; REFUSED {len(refused)} outside {allowed}: {', '.join(refused)}" if refused else ""))
        print(f"build_model: model notes: {str(out.get('notes', ''))[:300]}")
        for r in rejected:
            print(f"build_model: REJECTED (kept the previous version) {r}")
        code, output = run_tests(root, test_cmd)
        if rejected:
            code = code or 1
            output = "FILES REJECTED because they do not parse (the previous versions were kept; write the whole file again, correctly):\n" \
                     + "\n".join(rejected) + "\n\n" + output
        print(f"build_model: test command exited {code}; {raw.get('eval_count')} tokens in {raw.get('total_duration', 0) / 1e9:.0f}s")
        if code == 0:
            print("build_model: tests pass. Nothing is committed: read the diff, commit as yourself, then scan, hand off and gate.")
            return 0
        feedback = output
        if identical:
            # the same answer twice cannot be the fix: say so, and sample a little wider
            temperature = min(0.6, temperature + 0.25)
            feedback = ("YOUR PREVIOUS ANSWER WAS BYTE-IDENTICAL TO THE ONE BEFORE IT AND DID NOT FIX THE ERROR. Read the traceback "
                        "line by line; rewrite the failing function from scratch rather than editing it.\n" + output)
            print(f"build_model: round {rnd} changed nothing; temperature raised to {temperature}")
    print(f"build_model: tests still failing after {a.rounds} round(s); the tree is left as the model wrote it for the human to read")
    return 1


if __name__ == "__main__":
    sys.exit(main())
