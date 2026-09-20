# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A security-gate reviewer that runs on a local open-weight model (spec 03 §2.2; spec 11 §8).

Launched by `engine review` as a fresh process whose only argument is the handoff path:

    ENGINE_REVIEWER_CMD="python .engine/reviewers/local_model.py --model gemma4:31b-it-q4_K_M"
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
QUESTIONS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "manifest_result": {"type": "string"},
        "platform_surface": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "severity": {"type": "string", "enum": ["blocking", "non-blocking"]},
            "checklist_item": {"type": "string"}, "file": {"type": "string"}, "line": {"type": "integer"},
            "description": {"type": "string"}, "fix": {"type": "string"}},
            "required": ["id", "severity", "checklist_item", "file", "description"]}},
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


def ask(endpoint, model, system, user, num_ctx):
    body = {"model": model, "stream": False, "format": SCHEMA, "options": {"temperature": 0, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{endpoint}/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        out = json.loads(r.read().decode("utf-8"))
    return json.loads(out["message"]["content"]), out


def build_prompt(root, facts, checklist_text, definition, controls):
    base, head = facts["base"], facts["head"]
    diff = git(root, "diff", f"{base}..{head}", "--", ".", ":(exclude).engine/harness", ":(exclude).engine/records", ":(exclude).engine/local")
    if len(diff) > 120_000:
        diff = diff[:120_000] + "\n[diff truncated by the reviewer driver at 120000 characters; say so in the summary]\n"
    names = git(root, "diff", "--name-only", f"{base}..{head}")
    parts = [f"Unit {facts['unit']} run {facts['run']}. Range {base}..{head}.",
             f"Scan line from the handoff: {facts.get('scan', 'not stated')}", "",
             "Files changed in the range:", names, "",
             "Declared controls (from .engine/control-manifest.json):",
             json.dumps(controls, indent=1), "",
             "Checklist prepared for this run:", checklist_text, "",
             "Project rules (AGENTS.md, section Project rules):", _section(read(root / "AGENTS.md"), "## Project rules"), "",
             "Findings register (Table A rows are checks that must still exist):", read(root / ".engine/records/findings-register.md")[-4000:], "",
             "THE DIFF, read from version control at the range above:", "", diff, "",
             "Produce the verdict as JSON matching the schema. Rules:",
             "- Every checklist item gets a result and one line of evidence from the diff or the tree (file:line).",
             "- A finding names the checklist item, the file, the line, what is wrong, and the fix. Blocking findings make the verdict fail.",
             "- completeness: one object per declared control whose file is in the diff, keyed by control id; answer Q1..Q6 in prose;",
             "  Q3 and Q4 are lists (comma-separated or one per line). A bare 'pass' or 'n/a' is rejected by the harness.",
             "- manifest_result: what the manifest declares versus what the diff implements, in one sentence.",
             "- platform_surface: which platform-enforced controls (branch protection, secrets service, audit log destination) this change relies on, or 'none'.",
             "- Do not invent files or lines. If the diff does not show something, say it is not shown."]
    return "\n".join(parts)


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
    ap.add_argument("--reviewer-class", default="automated", choices=["automated", "automated-with-human-review"])
    ap.add_argument("handoff")
    a = ap.parse_args(argv)
    if not a.endpoint.startswith(LOOPBACK):
        print(f"local_model: REFUSED — endpoint {a.endpoint} is not the loopback interface; a local reviewer never leaves the box")
        return 2
    hp = pathlib.Path(a.handoff).resolve()
    root = hp.parent.parent.parent          # .engine/local/handoff-U-R.md -> project root
    facts = handoff_facts(read(hp))
    for k in ("unit", "run", "base", "head"):
        if k not in facts:
            print(f"local_model: COULD NOT RUN — handoff lacks {k}")
            return 2
    state_p = root / ".engine" / "local" / f"gate-{facts['unit']}-{facts['run']}.json"
    if not state_p.is_file():
        print(f"local_model: COULD NOT RUN — no prepared run at {state_p.name}; run `gate prepare` first")
        return 2
    state = json.loads(read(state_p))
    if not state.get("quality_passed"):
        print("local_model: STOP — the handoff's run did not pass the quality gate; the security gate does not run")
        return 1
    checklist_text = read(root / ".engine" / "local" / f"gate-{facts['unit']}-{facts['run']}-checklist.md")
    definition = read(root / ".engine" / "agents" / "security-gate.md")
    try:
        controls = json.loads(read(root / ".engine" / "control-manifest.json")).get("controls", [])
    except ValueError:
        controls = []
    controls = [c for c in controls if not c.get("placeholder")]
    try:
        identity = model_identity(a.endpoint, a.model)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"local_model: COULD NOT RUN — model runtime not reachable on the loopback interface ({e})")
        return 2
    system = definition + "\n\nYou answer only with the JSON object the schema describes."
    user = build_prompt(root, facts, checklist_text, definition, controls)
    print(f"local_model: reviewing {facts['unit']} run {facts['run']} with {identity}; prompt {len(user)} chars")
    try:
        judgment, raw = ask(a.endpoint, a.model, system, user, a.num_ctx)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"local_model: COULD NOT RUN — the model did not return a verdict ({e})")
        return 2
    findings = judgment.get("findings") or []
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
        "findings_detail": findings, "summary": judgment.get("summary", ""),
        "model_runtime": {"total_duration_s": round(raw.get("total_duration", 0) / 1e9, 1), "eval_count": raw.get("eval_count"),
                          "prompt_eval_count": raw.get("prompt_eval_count")},
    }
    slug = re.sub(r"[^A-Za-z0-9]+", "-", a.model).strip("-")
    out = root / ".engine" / "local" / f"verdict-{facts['unit']}-{facts['run']}-{slug}.json"
    out.write_text(json.dumps(block, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"local_model: {verdict.upper()} — {len(findings)} finding(s), {len(blocking)} blocking; "
          f"{block['model_runtime']['eval_count']} tokens in {block['model_runtime']['total_duration_s']}s")
    for f in findings:
        print(f"  - [{f.get('severity')}] {f.get('id')} {f.get('checklist_item')} {f.get('file')}:{f.get('line', '?')} — {f.get('description')}")
    print(f"local_model: verdict block written to {out.relative_to(root).as_posix()}; submit with `gate submit unit={facts['unit']} run={facts['run']} file=<that path> attested_by=<name>`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
