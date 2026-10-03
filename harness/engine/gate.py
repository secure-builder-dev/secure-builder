# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The two gates on the range (spec 01 §5, §6; spec 03 §2–4; spec 11).

`prepare` runs everything mechanical about a gate on a range and writes the
run state: the quality gate (coverage on the range, the negative-test set
from the generated route inventory, mutation of declared controls) and the
mechanical part of the security gate (the diff read from version control, the
control-shape decision, the manifest-entry rule, the findings register at
start, attribution and frozen-surface rules, the composed checklist). The
reviewing agent then applies the checklist in its own session and returns a
verdict block, which `submit` validates and records. With no model at all,
`no_model` records an advisory row: the mechanical checks ran and the
checklist was not applied, and the row says so.
"""
import json
import pathlib
import re

from . import checklist, controlshape, gitutil, governance, manifest, mutate, probes, routes, topology, version
from .checks import high_side_changes, reconciliation, coverage_range, findings_register
from .outcome import Outcome, State
from .records import findings as findings_mod
from .records import gatelog, now
from .records import schema as sch

ATTRIBUTION = re.compile("co-authored" + "-by|" + r"\bclaude\b|\banthropic\b|\bopenai\b|\bcopilot\b|generated with \[", re.I)
NEG_ASSERT = re.compile(r"(?i)\b(401|403|unauthori[sz]ed|forbidden|reject|denied|permission)\b")
CROSS_PRINCIPAL = re.compile(r"(?i)(?<![a-z])(other|another|second|different)[_ ]?(user|principal|tenant|account|owner)(?![a-z])")   # test_other_user_cannot_... counts
LAST_ADMIN = re.compile(r"(?i)\b(last|only|sole)[_ ]?(admin|owner|privileged)\b")
BARE = re.compile(r"(?i)^\s*(pass|ok|yes|no|n/a|none|done|fine|✓|✔|x|-|checked)\s*[.!]?\s*$")


def state_path(root, unit, run):
    return pathlib.Path(root) / ".engine" / "work" / f"gate-{unit}-{run}.json"


# --- quality gate ---

def negative_test_set(root, cfg, base, head):
    """REQ-5.2: for every route added or changed in the range, a test asserting
    rejection without credentials; for record-scoped routes, cross-principal
    rejection; for operations that can remove the last privileged principal, a
    test that it is prevented. Routes come from the generated inventory."""
    name = "negative-tests"
    inv = routes.inventory(root)
    changed = set(gitutil.changed_files(root, base, head))
    touched = [r for r in inv if r["file"] in changed]
    ops = [o for o in routes.privileged_operations(root) if o["file"] in changed]
    if not inv and not ops:
        return Outcome.nothing_yet(name, "HTTP routes", "the generated inventory holds no routes and no privileged operations — this section is empty, not passed")
    if not touched and not ops:
        return Outcome.nothing_yet(name, "routes added or changed in this range",
                                   f"{len(inv)} route(s) exist; none is in the range — this section is empty, not passed")
    tests = _test_texts(root)
    findings = []
    for r in touched:
        mentions = route_mention(r["path"])
        hits = [t for t, text in tests.items() if mentions.search(text) and NEG_ASSERT.search(text)]
        if not hits:
            findings.append(f"{r['method']} {r['path']} ({r['file']}:{r['line']}): no test asserts rejection without credentials")
        if r["record_scoped"]:
            cross = [t for t, text in tests.items() if mentions.search(text) and CROSS_PRINCIPAL.search(text)]
            if not cross:
                findings.append(f"{r['method']} {r['path']}: record-scoped, and no test asserts one principal cannot reach another's records")
    for o in ops:
        if not any(o["symbol"] in text and LAST_ADMIN.search(text) for text in tests.values()):
            findings.append(f"{o['symbol']} ({o['file']}:{o['line']}): can remove a privileged principal, and no test asserts the last one is protected")
    if findings:
        return Outcome.found(name, f"{len(findings)} negative-test gap(s) on {len(touched)} route(s) and {len(ops)} privileged operation(s)",
                             findings, blocking=True)
    return Outcome.clean(name, f"{len(touched)} route(s) and {len(ops)} privileged operation(s) in the range each have their rejection tests")


def route_mention(path):
    """A test names a templated route by a concrete instance: /notes/<id> is exercised by
    /notes/1, /notes/{note_id} by an f-string. Each parameter matches one path segment."""
    parts = re.split(r"(<[^>]+>|\{[^}]+\}|:\w+)", path)
    pattern = "".join(r"[^/\s'\"]+" if re.fullmatch(r"<[^>]+>|\{[^}]+\}|:\w+", x) else re.escape(x) for x in parts if x)
    return re.compile(pattern)


def _test_texts(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else []
    out = {}
    for f in files:
        if f.startswith(".engine/"):
            continue        # the placed harness's own fixtures are not the project's tests
        if controlshape.TEST_PATH.search(f) and pathlib.Path(f).suffix in routes.SOURCE_EXT:
            p = root / f
            if p.is_file():
                out[f] = p.read_text(encoding="utf-8", errors="replace")
    return out


def mutation_evidence(root, cfg):
    """REQ-5.3.1 / REQ-7.4.2: every declared control has a recorded mutation whose suite failed."""
    name = "control-mutation"
    try:
        data = manifest.load(root)
    except manifest.ManifestError as e:
        return Outcome.could_not_run(name, str(e))
    controls = manifest.real_controls(data)
    if not controls:
        return Outcome.nothing_yet(name, "declared controls", "the manifest declares no controls to mutate")
    rows, problems = mutate.read_results(root)
    if problems:
        return Outcome.could_not_run(name, "mutation results unreadable: " + "; ".join(problems[:2]))
    latest = {}
    for r in rows:
        latest[(r["control"], r["branch"])] = r["result"]
    findings = []
    for c in controls:
        for branch, _ in mutate.plan(c):
            res = latest.get((c["id"], branch))
            if res is None:
                findings.append(f"{c['id']} [{branch}]: never mutated — no result recorded")
            elif res != "suite-failed":
                findings.append(f"{c['id']} [{branch}]: last mutation left the suite green ({res}) — the tests do not depend on this control")
    if findings:
        return Outcome.found(name, f"{len(findings)} control(s) without a recorded failing mutation", findings, blocking=True)
    return Outcome.clean(name, f"{len(controls)} declared control(s) each have a recorded mutation that failed the suite")


def quality_gate(root, cfg, base, head):
    outs = [coverage_range.run(root, cfg, base, head), negative_test_set(root, cfg, base, head), mutation_evidence(root, cfg)]
    cmd = cfg.get("test_command")
    if cmd:
        from . import tools
        res = tools.run_tool(cmd[0], cmd[1:], cwd=str(root))
        if not res.ran:
            outs.append(Outcome.could_not_run("test-suite", f"test command '{cmd[0]}' is not on the search path"))
        elif res.exit_code != 0:
            outs.append(Outcome.found("test-suite", f"project suite exited {res.exit_code}", [(res.stdout + res.stderr).strip().splitlines()[-1:] or ["(no output)"]][0], blocking=True))
        else:
            outs.append(Outcome.clean("test-suite", f"project suite exited 0 ({' '.join(cmd)})"))
    else:
        outs.append(Outcome.could_not_run("test-suite", "no test_command configured; the project's suite was not run"))
    return outs


# --- security gate, mechanical part ---

def security_mechanical(root, cfg, base, head, unit):
    root = pathlib.Path(root)
    diff = gitutil.diff_text(root, base, head)
    changed = gitutil.changed_files(root, base, head)
    families = controlshape.diff_is_control_shaped(diff)
    outs, ctx = [], {"control_shaped": bool(families), "families": families}

    # REQ-7.4.1: control-shaped diff needs a manifest entry in the same change
    if families:
        try:
            data = manifest.load(root)
            entries = manifest.real_controls(data)
        except manifest.ManifestError:
            data, entries = None, []
        manifest_changed = manifest.FILE in changed
        entry_for_change = any(c["location"]["file"] in changed for c in entries)
        if not (manifest_changed and entry_for_change):
            outs.append(Outcome.found("manifest-entry", f"control-shaped diff ({', '.join(families)}) with no corresponding manifest entry in the same change",
                                      [f"{manifest.FILE} {'changed' if manifest_changed else 'unchanged'} in range; "
                                       f"{'an' if entry_for_change else 'no'} entry names a file changed in range"], blocking=True))
        else:
            outs.append(Outcome.clean("manifest-entry", f"control-shaped diff ({', '.join(families)}) declares its control in the same change"))
    else:
        outs.append(Outcome.nothing_yet("manifest-entry", "control-shaped changes", "the diff touches no authentication, authorization, audit, redaction, cryptography or scoping code"))

    outs.append(findings_register.run(root, cfg))                       # read at gate start
    outs.append(_attribution(root, base, head, diff))                   # spec 03 REQ-4.5
    outs.append(_frozen_surface(root, cfg, changed))                    # spec 03 REQ-4.6–4.7
    outs.append(_plans_during_construction(root, changed, unit, base, head))   # spec 03 REQ-3.5.1–3.5.2
    outs.append(_dependency_lead_time(root, cfg, diff))                 # spec 01 §6.2.1 item 10; spec 04 §10.6
    outs.append(probes.run_probe(root, cfg, head))                       # spec 01 §9.1–9.2: the standing-state probe, per gate
    outs.append(reconciliation.run(root, cfg))                            # spec 11 REQ-7.2, 7.5, 7.7: open field debt, at every gate
    if cfg.topology != "single":
        outs.append(high_side_changes.run(root, cfg))                     # spec 04 REQ-10.4.3: unported count at every gate
        outs.append(_originated_without_record(root, cfg, base, head))    # spec 04 REQ-10.4.1: no high-side change without a record
    gov_outs, is_gov = governance.check_range(root, cfg, base, head, unit)   # spec 01 §11
    outs += gov_outs
    ctx["governance"] = is_gov
    if is_gov:
        ctx["rules_at_base"] = governance.rules_at_base(root, base, governance.governed_set(root, cfg),
                                                        root / ".engine" / "work" / f"rules-at-base-{unit}")
    ctx["checklist"] = checklist.compose(cfg)
    ctx["checklist_version"] = checklist.version()
    return outs, ctx


def _originated_without_record(root, cfg, base, head):
    name = "high-side-origin"
    if cfg.side != "high":
        return Outcome.not_applicable(name, f"side '{cfg.side}'", "changes originate here by design; only the high side receives code it did not build",
                                      "the low-side gate log")
    recorded = {r["commit"][:12] for r in topology.changes(root)[0]}
    missing = [c for c in topology.originated_here(root, cfg, base, head) if c[:12] not in recorded]
    if missing:
        return Outcome.found(name, "the range carries content no received drop delivered and no high-side change record names",
                             [f"{c[:12]}: record it with what changed, why it could not wait for the low-side path, who authorized it, and its back-port status" for c in missing],
                             blocking=True)
    return Outcome.clean(name, "every commit in the range is received content or a recorded high-side change")


def _attribution(root, base, head, diff):
    hits = []
    for s in gitutil.git(root, "log", "--format=%B", f"{base}..{head}").stdout.splitlines():
        m = ATTRIBUTION.search(s)
        if m:
            hits.append(f"commit message: {m.group(0)!r}")
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++") and ATTRIBUTION.search(line):
            hits.append(f"added line: {line[1:].strip()[:70]}")
    if hits:
        return Outcome.found("attribution", "an agent attributed itself in something that lands in the repository", hits, blocking=True)
    return Outcome.clean("attribution", "no agent attribution in commit messages or added lines")


def _frozen_surface(root, cfg, changed):
    frozen = list(cfg.get("frozen_surface") or [])
    if not frozen:
        return Outcome.nothing_yet("frozen-surface", "declared frozen surface", "no frozen_surface paths are configured")
    root = pathlib.Path(root)
    touched = [f for f in changed if any(f == p or f.startswith(p.rstrip("/") + "/") for p in frozen)]
    report = []
    for p in frozen:
        path = root / p
        files = [path] if path.is_file() else sorted(x for x in path.rglob("*") if x.is_file()) if path.is_dir() else []
        keys = 0
        for f in files:
            keys += len(re.findall(r"^\s*[\w.-]+\s*[:=]", f.read_text(encoding="utf-8", errors="replace"), re.M))
        report.append(f"{p}: {len(files)} file(s), {keys} key(s) present, values not shown")
    if touched:
        return Outcome.found("frozen-surface", "the range writes directly to a frozen surface (propose, never write)",
                             [f"changed: {f}" for f in touched] + report, blocking=True)
    return Outcome.clean("frozen-surface", "; ".join(report))


def _plans_during_construction(root, changed, unit, base=None, head=None):
    """Design documents change in planning, not in construction (spec 03 REQ-3.5.1–3.5.2). The
    line is drawn per commit: a commit in which the unit file says anything but 'planned' is a
    construction commit, and a plan file it touches is a finding. The unit file's own state
    header is lifecycle state, not design, and never counts."""
    plan_files = [f for f in changed if f.startswith("plans/")]
    unit_rel = f"plans/units/{unit}.md"
    if not [f for f in plan_files if f != unit_rel]:
        return Outcome.clean("plan-edits", "no design document changed in the range")
    root = pathlib.Path(root)
    unit_file = root / unit_rel
    state = _header(unit_file).get("state", "") if unit_file.is_file() else ""
    if state == "planned" or not state:
        return Outcome.clean("plan-edits", f"{len(plan_files)} design document(s) changed while the unit is in planning")
    edited = []
    if base and head:
        for c in gitutil.commits_in(root, base, head):
            shown = gitutil.git(root, "show", f"{c}:{unit_rel}")
            st = _header_text(shown.stdout).get("state", "") if shown.returncode == 0 else ""
            if not st or st == "planned":
                continue                                                  # a planning commit: the unit is not yet building
            res = gitutil.git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", c)
            edited += [f for f in res.stdout.splitlines() if f.startswith("plans/") and f != unit_rel]
        edited = sorted(set(edited))
    else:
        edited = [f for f in plan_files if f != unit_rel]
    if not edited:
        return Outcome.clean("plan-edits", f"{len(plan_files)} design document(s) changed, all before construction began")
    return Outcome.found("plan-edits", f"design documents changed during construction (unit state '{state}')",
                         [f"{f}: a decision the plan did not anticipate requires a planning session, a recorded decision, and re-cut items"
                          for f in edited], blocking=True)


def _header_text(text):
    out = {}
    for line in text.splitlines():
        if not line.strip():
            break
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def _dependency_lead_time(root, cfg, diff):
    added = []
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            m = None
            if current.endswith(("package.json",)):
                m = re.match(r'\s*"([\w@./-]+)"\s*:\s*"[^"]+"', line[1:])
            elif current.endswith(("requirements.txt", "requirements-dev.txt", "pyproject.toml", "build.gradle", "build.gradle.kts")):
                m = re.match(r"\s*([A-Za-z0-9_.-]+)\s*(?:[=~<>!]|$)", line[1:]) if "requirements" in current else re.search(r"implementation\s*\(?['\"]([^'\"]+)", line[1:])
            if m and m.group(1) not in ("name", "version", "scripts", "dependencies", "devDependencies", "description", "main", "license"):
                added.append((current, m.group(1)))
    if not added:
        return Outcome.clean("dependency-policy", "no dependency added in the range")
    policy = _dependency_policy(root)
    if policy is None:
        return Outcome.found("dependency-policy", f"{len(added)} dependency(ies) added and no dependency policy document exists",
                             [f"{f}: {d} — record approval state and the date it became available on the target" for f, d in added],
                             blocking=True)
    requires = bool(policy.get("target_requires_approval")) or (cfg.topology != "single")
    findings = []
    for f, d in added:
        entry = policy.get("dependencies", {}).get(d)
        if entry is None:
            findings.append(f"{d}: not recorded in the dependency policy" + (f" — lead time to approval and transfer: {policy.get('lead_time', 'unstated')}" if requires else ""))
        elif requires and (entry.get("approval") != "approved" or not entry.get("available_on_target")):
            findings.append(f"{d}: approval={entry.get('approval', 'none')}, available on target: {entry.get('available_on_target') or 'not yet'}"
                            f" — lead time: {policy.get('lead_time', 'unstated')}; the branch cannot be built where it is going")
    if findings:
        return Outcome.found("dependency-policy", f"{len(findings)} of {len(added)} added dependencies fail the policy", findings, blocking=requires or True)
    return Outcome.clean("dependency-policy", f"{len(added)} added dependency(ies) recorded" + (" and approved for the target" if requires else ""))


def _dependency_policy(root):
    p = pathlib.Path(root) / ".engine" / "rules" / "dependency-policy.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _header(path):
    """A simple `key: value` header block at the top of an item or unit file."""
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            break
        m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


# --- orchestration ---

def prepare(root, cfg, unit, run, base, head):
    """Run both gates' mechanical parts; write the run state; return (quality outs, security outs, ctx)."""
    q = quality_gate(root, cfg, base, head)
    q_pass = not any(o.failed for o in q)
    s, ctx = security_mechanical(root, cfg, base, head, unit) if q_pass else ([], {"control_shaped": None, "checklist": [], "checklist_version": checklist.version()})
    state = {"unit": unit, "run": run, "base": base, "head": head, "quality_passed": q_pass,
             "quality": [o.line() for o in q], "security_mechanical": [o.line() for o in s],
             "mechanical_blocking": [o.check for o in s if o.state is State.FINDINGS and o.blocking],
             "control_shaped": ctx.get("control_shaped"), "families": ctx.get("families", []),
             "governance": bool(ctx.get("governance")),
             "checklist_version": ctx["checklist_version"], "harness_version": version(), "prepared": now(cfg)}
    p = state_path(root, unit, run)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if q_pass:
        _write_checklist(root, unit, run, ctx)
    return q, s, ctx


def _write_checklist(root, unit, run, ctx):
    L = [f"# Security gate checklist — {unit} run {run}", f"checklist version: {ctx['checklist_version']}",
         f"control-shaped: {'yes (' + ', '.join(ctx['families']) + ')' if ctx['control_shaped'] else 'no'}", ""]
    for group, i, text, detail, std in ctx["checklist"]:
        L.append(f"- [{group}] {i}. {text}" + (f" — {detail}" if detail else "") + (f" (cites: {std})" if std else ""))
    if ctx.get("governance"):
        L += ["", "GOVERNANCE CHANGE: this range alters the rule set. Evaluate against the rules as they existed at the",
              f"base commit, materialised under .engine/work/rules-at-base-{unit}/ ({len(ctx.get('rules_at_base', []))} file(s)).",
              "Your verdict is advisory; the accountable control is the human's line-by-line diff review."]
    if ctx["control_shaped"]:
        L += ["", "Completeness review (answer in prose per control touched; Q3 and Q4 produce a list):"]
        L += [f"- {q}: {t}" for q, t in checklist.COMPLETENESS]
    (pathlib.Path(root) / ".engine" / "work" / f"gate-{unit}-{run}-checklist.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


ONE_ITEM = re.compile(r"^\s*(?!.*[.!?]\s*$)[\w./:<>{}\[\]()-]+(?:\s+[\w./:<>{}\[\]()-]+){0,3}\s*$")


def is_enumeration(answer):
    """A list: several items with markers or commas, or a single bare item such as
    `DELETE /notes/<id>` — an identifier phrase of at most four tokens that names a route,
    symbol or path and does not end like a sentence. 'It covers everything.' is a summary
    judgment, not a list."""
    a = str(answer).strip()
    if re.search(r"(^|\n)\s*[-*\d]|,", a):
        return True
    return bool(ONE_ITEM.match(a) and (len(a.split()) <= 2 or re.search(r"[/:<>{}\[\]()_]|\w\.\w", a)))


def validate_verdict(state, v):
    """Problems with a submitted verdict block (spec 01 §6.5.1, §6.3.2–6.3.6)."""
    probs = []
    for f in checklist.VERDICT_FIELDS:
        if f not in v or str(v[f]).strip() == "":
            probs.append(f"verdict block lacks '{f}'")
    if probs:
        return probs
    if v["verdict"] not in ("pass", "fail"):
        probs.append("verdict must be pass or fail")
    if v["reviewer_class"] not in sch.REVIEWER_CLASSES:
        probs.append(f"reviewer_class must be one of {sch.REVIEWER_CLASSES}")
    if str(v["checklist_version"]) != state["checklist_version"]:
        probs.append(f"checklist_version {v['checklist_version']} is not the version this run was prepared with ({state['checklist_version']})")
    if str(v["range"]).replace(" ", "") != f"{state['base'][:12]}..{state['head'][:12]}" and str(v["range"]) != f"{state['base']}..{state['head']}":
        probs.append("range in the verdict is not the range this run was prepared on")
    if str(v["model"]).strip().lower() in ("", "-", "unknown", "n/a") and v["reviewer_class"] != "human":
        probs.append("model identity (identifier and parameter scale) must be recorded for an automated reviewer")
    if state.get("control_shaped"):
        answers = v.get("completeness") or {}
        if not isinstance(answers, dict) or not answers:
            probs.append("control-shaped diff: completeness review answers are required per control touched")
        else:
            for control, per_q in answers.items():
                if not isinstance(per_q, dict):
                    probs.append(f"completeness for {control}: answers must be given per question")
                    continue
                for q, _ in checklist.COMPLETENESS:
                    a = str(per_q.get(q, "")).strip()
                    if not a or BARE.match(a):
                        probs.append(f"completeness {control} {q}: unanswered or answered with a bare pass — blocking")
                    elif q in checklist.ENUMERATE and not is_enumeration(a):
                        probs.append(f"completeness {control} {q}: must produce a list, not a summary judgment")
        if v["verdict"] == "pass" and any("completeness" in p for p in probs):
            pass
    if v["verdict"] == "pass" and state.get("mechanical_blocking"):
        probs.append(f"verdict cannot be pass: mechanical checks blocked ({', '.join(state['mechanical_blocking'])})")
    return probs


def submit(root, cfg, unit, run, v, attested_by):
    """Validate and record a verdict block for a prepared run. Returns (row line, problems)."""
    p = state_path(root, unit, run)
    if not p.is_file():
        return None, [f"no prepared run {unit}#{run}; run `gate prepare` first"]
    state = json.loads(p.read_text(encoding="utf-8"))
    if not state["quality_passed"]:
        return None, ["the quality gate did not pass on this run; the security gate runs only after it (REQ-6.1.4)"]
    probs = validate_verdict(state, v)
    if probs:
        return None, probs
    if not str(attested_by).strip():
        return None, ["a named human must attest the unit of work"]
    ids = [str(x) for x in (v.get("finding_ids") or [])]
    count = int(v["open_findings"])
    verdict = v["verdict"]
    if state.get("governance"):
        verdict = "advisory"       # spec 01 REQ-11.2.1: the automated gate is advisory on a governance change
    if count and len(ids) != count:
        return None, [f"open_findings is {count} but {len(ids)} finding identifiers were given"]
    line = gatelog.append(root, cfg, unit=unit, range=f"{state['base'][:12]}..{state['head'][:12]}", run=str(run),
                          verdict=verdict, findings="0" if not count else f"{count}: {', '.join(ids)}",
                          tickets=", ".join(str(x) for x in (v.get("tickets_opened_ids") or [])) or "-",
                          reviewer=str(v.get("reviewer", "security-gate")), reviewer_class=v["reviewer_class"],
                          model=str(v["model"]), attested_by=attested_by, harness_version=state["harness_version"],
                          checklist_version=state["checklist_version"], controls=", ".join(v.get("controls_assessed") or []) or "-")
    state["verdict"] = v
    state["recorded"] = now(cfg)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return line, []


def no_model(root, cfg, unit, run, attested_by):
    """Record a run performed with no model at all (spec 11 REQ-8.1): mechanical
    checks and a record; the checklist was not applied and the row says so."""
    p = state_path(root, unit, run)
    if not p.is_file():
        return None, [f"no prepared run {unit}#{run}"]
    state = json.loads(p.read_text(encoding="utf-8"))
    blocking = state.get("mechanical_blocking", []) + ([] if state["quality_passed"] else ["quality-gate"])
    line = gatelog.append(root, cfg, unit=unit, range=f"{state['base'][:12]}..{state['head'][:12]}", run=str(run),
                          verdict="advisory", findings="0" if not blocking else f"{len(blocking)}: " + ", ".join(blocking),
                          reviewer="mechanical-only", reviewer_class="automated", model="none — checklist not applied",
                          attested_by=attested_by, harness_version=state["harness_version"],
                          checklist_version=state["checklist_version"])
    return line, []


def abandon(root, cfg, unit, run, reason, attested_by):
    """Close a started run that will never get a verdict (its handoff was stale, the range was
    replaced) with an 'abandoned' row: the marker is matched honestly, and nobody claims a review
    happened. The range comes from the run's started marker."""
    if not str(reason).strip() or not str(attested_by).strip():
        return None, ["an abandoned run needs a reason and the name of who abandoned it"]
    marker = next((m for m in gatelog.started_markers(root) if m.get("unit") == unit and str(m.get("run")) == str(run)), None)
    if marker is None:
        return None, [f"no started marker for {unit}#{run}: a run that never started needs no row"]
    if (unit, str(run)) not in {(m.get("unit"), str(m.get("run"))) for m in gatelog.unmatched_markers(root)}:
        return None, [f"{unit}#{run} already has a completed row"]
    p = state_path(root, unit, run)
    state = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    base, _, head = str(marker.get("range", "")).partition("..")
    line = gatelog.append(root, cfg, unit=unit, range=f"{base[:12]}..{head[:12]}", run=str(run), verdict="abandoned",
                          findings=f"1: ABANDONED - {reason}", reviewer="none", reviewer_class="automated",
                          model="none - run abandoned", attested_by=attested_by,
                          harness_version=state.get("harness_version", version()),
                          checklist_version=state.get("checklist_version", "-"))
    return line, []

