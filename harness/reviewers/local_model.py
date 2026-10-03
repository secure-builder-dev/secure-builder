# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A security-gate reviewer that runs on a local open-weight model (spec 03 §2.2; spec 11 §8).

Launched by `engine review` as a fresh process whose only argument is the handoff path:

    ENGINE_REVIEWER_CMD="python .engine/harness/reviewers/local_model.py --model gemma4:31b-it-q4_K_M"
    python .engine/harness/run.py review unit=U1 run=2

Everything else the reviewer needs is read from version control and the placed
definitions — the diff at the range the handoff names, the checklist the gate
prepared, the security-gate definition, the control manifest, the findings
register — never from the conversation that wrote the code. The model is reached
on the loopback interface only; any other endpoint is refused, so an air-gapped
box stays air-gapped. The facts of the run (range, versions, model identity) are
filled from the record; the model supplies the judgment: findings, completeness
answers per control, the verdict. Its output is written as the verdict block for
`gate submit`, where a named human attests.
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
THINK = {}          # {"think": False} when --no-think: a model's hidden reasoning is not spent from the answer's budget
QUESTIONS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "manifest_result": {"type": "string"},
        "platform_surface": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "severity": {"type": "string", "enum": ["blocking", "non-blocking"]},
            "checklist_item": {"type": "string"}, "file": {"type": "string"}, "quote": {"type": "string"},
            "description": {"type": "string"}, "fix": {"type": "string"}},
            "required": ["id", "severity", "checklist_item", "file", "quote", "description", "fix"]}},
        "checklist": {"type": "array", "items": {"type": "object", "properties": {
            "item": {"type": "string"}, "result": {"type": "string", "enum": ["pass", "finding", "not-applicable"]},
            "evidence": {"type": "string"}}, "required": ["item", "result", "evidence"]}},
        "completeness": {"type": "object", "additionalProperties": {"type": "object", "properties": {
            q: {"type": "string"} for q in QUESTIONS}, "required": QUESTIONS}},
        "summary": {"type": "string"},
    },
    "required": ["verdict", "manifest_result", "platform_surface", "findings", "checklist", "completeness", "summary"],
}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def read(p):
    p = pathlib.Path(p)
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def read_at(root, head, rel):
    """A file as version control holds it at the range head — the manifest, the project rules and the
    register the reviewer judges against are the ones the code under review was committed with, not
    whatever the working tree holds when the review happens to run (a bake-off replays old handoffs)."""
    res = subprocess.run(["git", "-C", str(root), "show", f"{head}:{rel}"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return res.stdout if res.returncode == 0 else read(pathlib.Path(root) / rel)


def handoff_facts(text):
    facts = {}
    for line in text.splitlines():
        m = re.match(r"^# GATE HANDOFF: (\S+) run (\d+)", line)
        if m:
            facts["unit"], facts["run"] = m.group(1), m.group(2)
        m = re.match(r"^range: ([0-9a-f]+)\.\.([0-9a-f]+)", line)
        if m:
            facts["base"], facts["head"] = m.group(1), m.group(2)
        m = re.match(r"^scan: (.*)$", line)
        if m:
            facts["scan"] = m.group(1)
        m = re.match(r"^read first: (.*)$", line)
        if m:
            facts["read_first"] = [x.strip() for x in m.group(1).split(",")]
    return facts


def model_identity(endpoint, model):
    """Identifier and parameter scale from the runtime, never typed by hand (spec 11 REQ-8.2)."""
    req = urllib.request.Request(f"{endpoint}/api/show", data=json.dumps({"name": model}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        info = json.loads(r.read().decode("utf-8"))
    d = info.get("details", {})
    digest = ""
    with urllib.request.urlopen(f"{endpoint}/api/tags", timeout=60) as r:
        for m in json.loads(r.read().decode("utf-8")).get("models", []):
            if m.get("name") == model or m.get("model") == model:
                digest = m.get("digest", "")[:12]
    return f"{model} ({d.get('family', '?')}; {d.get('parameter_size', '?')}; {d.get('quantization_level', '?')}; ollama digest {digest or '?'})"


class NoVerdict(ValueError):
    """The model answered but not with the JSON object the schema describes; the raw answer is kept."""


def ask(endpoint, model, system, user, num_ctx, raw_path=None):
    body = {"model": model, "stream": False, "format": SCHEMA, "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], **THINK}
    req = urllib.request.Request(f"{endpoint}/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        out = json.loads(r.read().decode("utf-8"))
    msg = out.get("message") or {}
    try:
        return json.loads(msg["content"]), out
    except (ValueError, KeyError) as e:
        if raw_path:
            # the raw answer is the only evidence of what went wrong: kept beside the verdicts, never parsed leniently
            raw_path.write_text(json.dumps({k: v for k, v in out.items() if k != "context"}, indent=1), encoding="utf-8", newline="\n")
        raise NoVerdict(f"{e}; done_reason={out.get('done_reason')!r}, eval_count={out.get('eval_count')}, "
                        f"content={len(str(msg.get('content', '')))} chars, thinking={len(str(msg.get('thinking', '')))} chars"
                        + (f"; raw answer kept at {raw_path.name}" if raw_path else ""))


VENDORED_DIRS = frozenset({"vendor", "vendored", "third_party", "third-party", "node_modules"})
MAX_FILE_LINES = 1500        # a text diff longer than this is bulk data, not code to review
MAX_FILE_BYTES = 40_000


def vendored(path):
    return any(part in VENDORED_DIRS for part in path.split("/")[:-1])


def held_back_files(numstat):
    """Split `git diff --numstat` into (text files to show, summaries of the rest). Vendored third-party
    files, binary files and very large text diffs are summarized by folder, not pasted: minified Leaflet
    put the antipode A-2 review at 47K tokens, and 1365 binary map tiles put A-4's at 60K."""
    shown, groups = [], {}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, name = parts
        binary = added == "-" and deleted == "-"
        big = not binary and int(added) + int(deleted) > MAX_FILE_LINES
        if not (binary or big or vendored(name)):
            shown.append(name)
            continue
        kind = "vendored third-party" if vendored(name) else "binary" if binary else "bulk data"
        # grouped by the first three folders: map tiles nest as tiles/<z>/<x>/, and 63 lines for one data set say nothing more than one
        folder = "/".join(name.split("/")[:-1][:3]) + "/" if "/" in name else "./"
        groups.setdefault((folder, kind), []).append(name)
    held = [f"{folder}: {len(names)} {kind} file(s), not shown" + (f" ({names[0]})" if len(names) == 1 else "")
            for (folder, kind), names in sorted(groups.items())]
    return shown, held


def build_prompt(root, facts, checklist_text, definition, controls):
    base, head = facts["base"], facts["head"]
    # the project's change: everything but the placed harness; the governed files under .engine/ are part of the change
    # vendored third-party code and bulk data are listed, not pasted: minified Leaflet alone put the
    # antipode A-2 review at 47K tokens; the reviewer judges the project's code, integrity is pinned elsewhere
    shown, held = held_back_files(git(root, "diff", "--numstat", f"{base}..{head}", "--", ".", ":(exclude).engine"))
    for name in list(shown):        # a one-line data file (a 172 KB GeoJSON) is bulk by size, not by line count
        size = git(root, "cat-file", "-s", f"{head}:{name}").strip()
        if size.isdigit() and int(size) > MAX_FILE_BYTES:
            shown.remove(name)
            held.append(f"{name}: bulk data, {size} bytes, not shown")
    diff = (git(root, "diff", f"{base}..{head}", "--", *shown) if shown else "") \
        + git(root, "diff", f"{base}..{head}", "--", ".engine/rules/control-manifest.json", ".engine/rules/config.json", ".engine/rules/governance.json", ".engine/rules/dependency-policy.json")
    if held:
        diff += "\nFiles in the range not shown in this diff:\n" + "\n".join(held) + "\n"
    if len(diff) > 120_000:
        diff = diff[:120_000] + "\n[diff truncated by the reviewer driver at 120000 characters; say so in the summary]\n"
    names = "\n".join(shown + held + [n for n in git(root, "diff", "--name-only", f"{base}..{head}", "--", ".engine/rules").splitlines()])
    register = read_at(root, head, ".engine/records/findings-register.md")
    register = register if re.search(r"^\| (F|R|AUD)-", register, re.M) else ""     # a template-only register says nothing
    controls = [{k: c.get(k) for k in ("id", "description", "location", "test_pattern", "status")} for c in controls]
    parts = [f"Unit {facts['unit']} run {facts['run']}. Range {base}..{head}.",
             f"Scan line from the handoff: {facts.get('scan', 'not stated')}", "",
             "Files changed in the range:", names, "",
             "Declared controls (from .engine/rules/control-manifest.json):",
             json.dumps(controls, indent=1), "",
             "Checklist prepared for this run:", checklist_text, "",
             "Project rules (AGENTS.md, section Project rules):", _section(read_at(root, head, "AGENTS.md"), "## Project rules"), "",
             *(["Findings register (Table A rows are checks that must still exist):", register[-4000:], ""] if register else []),
             "THE DIFF, read from version control at the range above:", "", diff, "",
             "Produce the verdict as JSON matching the schema. Rules:",
             "- Every checklist item gets a result and one line of evidence. An item about something this change does not contain",
             "  (cloud infrastructure, uploads, dependencies, database queries, classification marking) is 'not-applicable' with the",
             "  evidence 'not in this change' — it is NOT a finding. Items marked informational are never blocking.",
             "- A finding is raised only against code the diff shows. Each finding MUST carry 'quote': one line copied verbatim from",
             "  the diff (the code line, without the leading + sign). The harness checks the quote exists; a finding whose quote is",
             "  not in the diff is discarded as ungrounded and counted against the reviewer. Prefer few, real findings.",
             "- Blocking means: exploitable or a rejected-case test missing. Style, naming and hypothetical concerns are non-blocking.",
             "- completeness: one object per declared control whose file is in the diff, keyed by control id; answer Q1..Q6 in prose;",
             "  Q3 and Q4 are lists (comma-separated or one per line). A bare 'pass' or 'n/a' is rejected by the harness.",
             "- manifest_result: what the manifest declares versus what the diff implements, in one sentence.",
             "- platform_surface: which platform-enforced controls (branch protection, secrets service, audit log destination) this change relies on, or 'none'.",
             "- Do not invent files or lines. If the diff does not show something, say it is not shown."]
    return "\n".join(parts)


BARE = re.compile(r"(?i)^\s*(pass|ok|yes|no|n/a|none|done|fine|x|-|checked|not applicable)\s*[.!]?\s*$")
ENUMERATE = ("Q3", "Q4")
ONE_ITEM = re.compile(r"^\s*(?!.*[.!?]\s*$)[\w./:<>{}\[\]()-]+(?:\s+[\w./:<>{}\[\]()-]+){0,3}\s*$")   # a one-item list, e.g. `DELETE /notes/<id>`


def is_enumeration(a):
    a = str(a).strip()
    if re.search(r"(^|\n)\s*[-*\d]|,", a):
        return True
    return bool(ONE_ITEM.match(a) and (len(a.split()) <= 2 or re.search(r"[/:<>{}\[\]()_]|\w\.\w", a)))


def completeness_problems(answers, controls):
    """The harness's own rules, applied before submission (spec 01 §6.3): every control in the
    diff answered, no bare answer, Q3/Q4 produce a list."""
    probs = []
    for c in controls:
        per = answers.get(c["id"])
        if not isinstance(per, dict):
            probs.append(f"{c['id']}: no answers")
            continue
        for q in QUESTIONS:
            v = str(per.get(q, "")).strip()
            if not v or BARE.match(v):
                probs.append(f"{c['id']} {q}: bare or empty answer; write what you examined")
            elif q in ENUMERATE and not is_enumeration(v):
                probs.append(f"{c['id']} {q}: must be a list — enumerate items (comma-separated or one per line); "
                             "if you believe nothing is uncovered, list the entry points you examined and state each is covered")
    return probs


def repair_completeness(endpoint, model, system, user, answers, controls, num_ctx, passes=3):
    """Up to `passes` structured follow-ups: each time the model is told exactly which answers the
    harness will refuse; the best set (fewest refusals) is kept. One pass was not enough on antipode
    ANTI-2 run 4: a single bare answer kept a grounded FAIL out of the record."""
    best, best_probs = answers, completeness_problems(answers, controls)
    if not best_probs:
        return answers
    schema = {"type": "object", "properties": {c["id"]: {"type": "object", "properties": {q: {"type": "string"} for q in QUESTIONS},
                                                           "required": QUESTIONS} for c in controls}, "required": [c["id"] for c in controls]}
    NL = chr(10)
    for n in range(1, passes + 1):
        print(f"local_model: completeness answers would be refused ({len(best_probs)}); repair pass {n} of {passes}")
        ask_text = (user + NL + NL + "Your completeness answers were:" + NL + json.dumps(best, indent=1) + NL + NL
                    + "The harness refuses them for these reasons:" + NL + "- " + (NL + "- ").join(best_probs) + NL + NL
                    + "Answer the completeness questions again for every control, as JSON keyed by control id. Every answer says "
                    + "what you examined in a full sentence or list; never a bare yes, no, pass or n/a. Q3 and Q4 are LISTS "
                    + "in exactly this shape, one item per line, each item a route, symbol or condition, never a sentence:" + NL
                    + "- GET /notes" + NL + "- token expiry" + NL + "If nothing is uncovered, list what you examined: '- GET /notes (covered)'.")
        body = {"model": model, "stream": False, "format": schema,
                "options": {"temperature": 0.0 if n == 1 else 0.2 * (n - 1), "num_ctx": num_ctx, "num_predict": 8192},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": ask_text}], **THINK}
        req = urllib.request.Request(f"{endpoint}/api/chat", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3600) as r:
                fixed = json.loads(json.loads(r.read().decode("utf-8"))["message"]["content"])
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            continue
        left = completeness_problems(fixed, controls)
        print(f"local_model: after repair pass {n}, {len(left)} completeness problem(s) remain" + (": " + "; ".join(left[:3]) if left else ""))
        if len(left) < len(best_probs):
            best, best_probs = fixed, left
        if not best_probs:
            break
    return best


def substantive(quote):
    """A quote grounds a finding only if it could only have come from this diff: at least eight
    non-space characters including a word of three letters or more. A lone `]`, `}` or `return`
    is in every diff and proves nothing (seen from Gemma 4 on NOTES-3: a manifest finding quoting `]`)."""
    return len(re.sub(r"\s", "", quote)) >= 8 and re.search(r"[A-Za-z_]{3,}", quote) is not None


def item_of(entry, item_ids, *fields):
    """The checklist item an entry refers to: the leading token of the first named field that is an item id
    (`B3` from `B3. Authorization ...`, or a field holding the bare id such as `ELEVATED1`). A model that puts
    the id in `id` and the item's prose in `checklist_item` is still held to the item's informational status
    and to its own pass/fail on that item."""
    for k in fields:
        head = str(entry.get(k, "")).split(".")[0].split(" ")[0]
        if head in item_ids:
            return head
    return str(entry.get(fields[0], "")).split(".")[0].split(" ")[0]


def _line_of(root, head, file, quote):
    """The line number of a quoted line in the file at head, from version control, not from the model."""
    text = git(root, "show", f"{head}:{file}") if file else ""
    for n, line in enumerate(text.splitlines(), 1):
        if re.sub(r"\s+", " ", line).strip() == quote:
            return n
    return None


def _section(text, header):
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            on = line.strip() == header
            continue
        if on:
            out.append(line)
    return "\n".join(out).strip() or "(none)"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--no-think", action="store_true", help="ask a reasoning model not to think aloud; recorded in the verdict")
    NL = chr(10)
    ap.add_argument("--reviewer-class", default="automated", choices=["automated", "automated-with-human-review"])
    ap.add_argument("handoff")
    a = ap.parse_args(argv)
    if not a.endpoint.startswith(LOOPBACK):
        print(f"local_model: REFUSED — endpoint {a.endpoint} is not the loopback interface; a local reviewer never leaves the box")
        return 2
    if a.no_think:
        THINK["think"] = False
    hp = pathlib.Path(a.handoff).resolve()
    root = hp.parent.parent.parent          # .engine/work/handoff-U-R.md -> project root
    facts = handoff_facts(read(hp))
    for k in ("unit", "run", "base", "head"):
        if k not in facts:
            print(f"local_model: COULD NOT RUN — handoff lacks {k}")
            return 2
    state_p = root / ".engine" / "work" / f"gate-{facts['unit']}-{facts['run']}.json"
    if not state_p.is_file():
        print(f"local_model: COULD NOT RUN — no prepared run at {state_p.name}; run `gate prepare` first")
        return 2
    state = json.loads(read(state_p))
    if not state.get("quality_passed"):
        print("local_model: STOP — the handoff's run did not pass the quality gate; the security gate does not run")
        return 1
    checklist_text = read(root / ".engine" / "work" / f"gate-{facts['unit']}-{facts['run']}-checklist.md")
    definition = read(root / ".engine" / "rules" / "agents" / "security-gate.md")
    try:
        controls = json.loads(read_at(root, facts["head"], ".engine/rules/control-manifest.json")).get("controls", [])
    except ValueError:
        controls = []
    controls = [c for c in controls if not c.get("placeholder")]
    try:
        identity = model_identity(a.endpoint, a.model)
    except urllib.error.HTTPError as e:
        print(f"local_model: COULD NOT RUN — the runtime does not hold model '{a.model}' (HTTP {e.code}); model weights are "
              "vendored data: pull them with provenance before the gate runs")
        return 2
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"local_model: COULD NOT RUN — model runtime not reachable on the loopback interface ({e})")
        return 2
    system = definition + "\n\nYou answer only with the JSON object the schema describes."
    user = build_prompt(root, facts, checklist_text, definition, controls)
    est = (len(system) + len(user)) // 3 + 1500        # a conservative token estimate plus room for the answer
    if est > a.num_ctx:
        print(f"local_model: COULD NOT RUN — the review needs about {est} tokens of context and the model is given {a.num_ctx}; "
              "a truncated diff is reviewed blind, and a blind review is not a review. Raise --num-ctx or split the range.")
        return 2
    print(f"local_model: reviewing {facts['unit']} run {facts['run']} with {identity}; prompt {len(user)} chars (~{est} tokens of {a.num_ctx})")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", a.model).strip("-")
    try:
        judgment, raw = ask(a.endpoint, a.model, system, user, a.num_ctx,
                            raw_path=root / ".engine" / "work" / f"raw-{facts['unit']}-{facts['run']}-{slug}.json")
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"local_model: COULD NOT RUN — the model did not return a verdict ({e})")
        return 2
    diff_lines = [l[1:] if l[:1] in "+ " else l for l in git(root, "diff", f"{facts['base']}..{facts['head']}").splitlines()]
    normalized = {re.sub(r"\s+", " ", l).strip() for l in diff_lines if l.strip()}
    informational = set(re.findall(r"^- \[[^\]]*informational\] (\w+)\.", checklist_text, re.M))
    item_ids = set(re.findall(r"^- \[[^\]]*\] (\w+)\.", checklist_text, re.M))
    judged = {item_of(c, item_ids, "item", "id"): c.get("result") for c in (judgment.get("checklist") or [])}
    judgment["completeness"] = repair_completeness(a.endpoint, a.model, system, user, judgment.get("completeness") or {}, controls, a.num_ctx)
    findings, ungrounded, inconsistent, notes = [], [], [], []
    for f in judgment.get("findings") or []:
        item = item_of(f, item_ids, "checklist_item", "id")
        q = re.sub(r"\s+", " ", str(f.get("quote", ""))).strip().lstrip("+").strip()
        if not q or q not in normalized or not substantive(q):
            ungrounded.append(f)          # not in the diff, or a bracket / brace / keyword that is in every diff
            continue
        if item in informational:
            notes.append(f)                       # informational for this tier: recorded, never a finding
            continue
        if judged.get(item) in ("pass", "not-applicable"):
            inconsistent.append(f)                # the reviewer's own checklist says this item is fine
            continue
        f["line"] = _line_of(root, facts["head"], f.get("file", ""), q)
        findings.append(f)
    blocking = [f for f in findings if f.get("severity") == "blocking"]
    verdict = "fail" if blocking else judgment.get("verdict", "fail")
    block = {
        "verdict": verdict, "tier": "security", "run": facts["run"], "range": f"{facts['base'][:12]}..{facts['head'][:12]}",
        "control_shaped": "yes" if state.get("control_shaped") else "no",
        "manifest_result": judgment.get("manifest_result", ""),
        "completeness_blocks": "yes" if any(str(v).strip() and re.match(r"(?i)^(pass|ok|n/a|none)$", str(v).strip()) for c in (judgment.get("completeness") or {}).values() for v in c.values()) else "no",
        "platform_surface": judgment.get("platform_surface", ""),
        "scan_verdict": facts.get("scan", "not stated"),
        "open_findings": len(findings), "blocking_findings": len(blocking), "tickets_opened": 0,
        "finding_ids": [f["id"] for f in findings], "tickets_opened_ids": [],
        "reviewer_class": a.reviewer_class, "model": identity, "attested_by": "(set at gate submit by the named human)",
        "checklist_version": state["checklist_version"], "harness_version": state["harness_version"],
        "completeness": judgment.get("completeness") or {}, "checklist": judgment.get("checklist") or [],
        "findings_detail": findings, "ungrounded_findings": ungrounded, "inconsistent_findings": inconsistent,
        "informational_notes": notes, "summary": judgment.get("summary", ""),
        "model_runtime": {"think": "off" if a.no_think else "model default", "thinking_chars": len(str((raw.get("message") or {}).get("thinking") or "")),
                          "total_duration_s": round(raw.get("total_duration", 0) / 1e9, 1), "eval_count": raw.get("eval_count"),
                          "prompt_eval_count": raw.get("prompt_eval_count")},
    }
    out = root / ".engine" / "work" / f"verdict-{facts['unit']}-{facts['run']}-{slug}.json"
    out.write_text(json.dumps(block, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"local_model: {verdict.upper()} — {len(findings)} grounded finding(s), {len(blocking)} blocking; "
          f"{len(ungrounded)} ungrounded (quote not in the diff), {len(inconsistent)} inconsistent (item judged pass), "
          f"{len(notes)} informational note(s); "
          f"{block['model_runtime']['eval_count']} tokens in {block['model_runtime']['total_duration_s']}s")
    for f in findings:
        print(f"  - [{f.get('severity')}] {f.get('id')} {f.get('checklist_item')} {f.get('file')}:{f.get('line') or '?'} — {f.get('description')}")
        print(f"      quote: {f.get('quote')}")
        print(f"      fix: {f.get('fix')}")
    for f in inconsistent:
        print(f"  - [inconsistent] {f.get('id')} {f.get('checklist_item')} — {f.get('description')[:100]}")
    for f in ungrounded:
        print(f"  - [ungrounded] {f.get('id')} {f.get('checklist_item')} — {f.get('description')} (quote: {str(f.get('quote'))[:80]!r})")
    print(f"local_model: verdict block written to {out.relative_to(root).as_posix()}; submit with `gate submit unit={facts['unit']} run={facts['run']} file=<that path> attested_by=<name>`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
