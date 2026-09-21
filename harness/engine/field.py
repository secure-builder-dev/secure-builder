# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Field mode (spec 11): one operator, under time pressure, no reachback.

Not a weaker gate — a bounded one that incurs a recorded debt. Entered only by
explicit declaration recording who, when and why; never inferred; never to
escape a failing check. The floor (credential scan, injection scan, manifest
verification, reference and citation integrity, the record write) always runs
and the budget is never enforced against it. Everything else may be deferred
by budget, recorded as *deferred* — a fourth state, distinct from passed,
skipped and not-applicable — and every deferral is a reconciliation obligation
that is counted, aged, reported at every gate, and discharged only by a full
re-gate that specifically confirms the deferred items. The field verdict is a
row of its own class in the ordinary gate log, stating its boundary in one
sentence a non-specialist can read.
"""
import datetime
import hashlib
import json
import pathlib
import time

from . import checklist, version
from .checks import (attack_surface, citations, control_manifest, coverage_range, credential_scan,
                     findings_register, injection_scan, license_policy, reference_integrity, scanner_pins)
from .outcome import Outcome, State
from .records import gatelog, now, table
from .records import schema as sch

DECLARATION = ".engine/work/field-mode.json"
LAST_CHECK = ".engine/work/last-check.json"
OBLIGATIONS = ".engine/records/reconciliation-obligations.md"
MODELS_DIR = ".engine/rules/models"
NO_MODEL = "none"

# The explicit table of what field mode changes (REQ-4.1). Nothing degrades that is not here.
DEGRADATION_TABLE = [
    ("two-window isolation", "retained — a separate reviewing session costs nothing but a second session"),
    ("human merge approval", "not achieved — stated in the verdict"),
    ("separation of duties", "not achieved — stated in the verdict"),
    ("control mutation", "deferrable — creates an obligation"),
    ("coverage thresholds on the range", "deferrable — creates an obligation"),
    ("full security checklist", "bounded by the budget — unrun items are listed as deferred, not omitted"),
    ("scan subsystem", "deferrable where the scanner cannot run on the hardware — creates an obligation"),
    ("standing-state probes", "deferrable — creates an obligation"),
    ("failure semantics", "unchanged — a check that runs and cannot complete its function does not exit zero"),
    ("records", "unchanged — the record matters more here, not less"),
]

# Floor: non-deferrable, in value-per-second order (cheapest, highest value first).
FLOOR = [("credential-scan", credential_scan.run), ("injection-scan", injection_scan.run),
         ("control-manifest", control_manifest.run), ("reference-integrity", reference_integrity.run),
         ("citations", citations.run)]
# Deferrable, ordered by cost: cheap mechanical work before the expensive suites.
DEFERRABLE = [("findings-register", findings_register.run), ("scanner-pins", scanner_pins.run),
              ("attack-surface", attack_surface.run), ("license-policy", license_policy.run),
              ("coverage-range", coverage_range.run), ("standing-state", None), ("control-mutation", None), ("scan", None)]


class FieldError(Exception):
    pass


def declaration(root):
    p = pathlib.Path(root) / DECLARATION
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def last_check(root):
    p = pathlib.Path(root) / LAST_CHECK
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def record_last_check(root, outcomes):
    p = pathlib.Path(root) / LAST_CHECK
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({o.check: {"state": o.state.value, "blocking": o.blocking} for o in outcomes}, indent=1, sort_keys=True) + "\n",
                 encoding="utf-8", newline="\n")


def open_obligations(root):
    rows, problems, versions = table.read(root, OBLIGATIONS, "reconciliation-obligations")
    if rows is None or problems or not versions:
        raise FieldError(f"{OBLIGATIONS} carries no readable reconciliation-obligations table" + (f": {problems[0]}" if problems else ""))
    latest = {}
    for r in rows or []:
        latest[r["id"]] = r
    return [r for r in latest.values() if r["status"] == "open"]


def aged_obligations(root, cfg):
    days = int((cfg.get("obligation_max_age_days") if cfg else None) or 30)
    today = datetime.date.today()
    out = []
    for r in open_obligations(root):
        try:
            age = (today - datetime.date.fromisoformat(r["opened"][:10])).days
        except ValueError:
            age = None
        if age is not None and age > days:
            out.append((r["id"], age))
    return out


def declare(root, cfg, *, by, reason, budget_seconds, impossible, accept_over_ceiling=""):
    """Explicit entry. Refuses when a deferrable check is currently failing (an escape
    hatch that absorbs a failure is a mechanism for passing with known defects), and
    when open obligations exceed the ceiling unless a named person records why."""
    if not by.strip() or not reason.strip() or not impossible.strip():
        raise FieldError("field mode is entered by explicit declaration: who, why (the operational reason), and what makes the full process impossible")
    failing = [name for name, st in last_check(root).items() if st["state"] == "checked-findings" and st["blocking"]
               and name in {n for n, _ in DEFERRABLE}]
    if failing:
        raise FieldError(f"field mode cannot be entered to escape a failing check: {', '.join(failing)} is failing now; "
                         "it is available where the full process is impossible, not where it is unwelcome")
    ceiling = int((cfg.get("obligation_ceiling") if cfg else None) or 5)
    open_ = open_obligations(root)
    if len(open_) >= ceiling and not accept_over_ceiling.strip():
        raise FieldError(f"{len(open_)} reconciliation obligations are open, at or above the ceiling of {ceiling}; entering field "
                         "mode again requires an explicit, recorded acceptance (accept_over_ceiling=\"why\") by a named person")
    data = {"declared_by": by.strip(), "declared_at": now(cfg), "reason": reason.strip(), "impossible": impossible.strip(),
            "budget_seconds": int(budget_seconds), "open_obligations_at_entry": len(open_),
            "over_ceiling_accepted": accept_over_ceiling.strip() or None}
    p = pathlib.Path(root) / DECLARATION
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def models(root):
    """Model weights are vendored data (REQ-8.5): each pinned model has a provenance file
    naming the weights file, its hash, version, parameter scale and source, exactly as a
    catalogue does. A model without provenance is not a model the verdict may name."""
    d = pathlib.Path(root) / MODELS_DIR
    out = {}
    if not d.is_dir():
        return out
    for prov in sorted(d.glob("*.provenance.json")):
        try:
            meta = json.loads(prov.read_text(encoding="utf-8"))
            for key in ("id", "file", "sha256", "version", "parameters", "source"):
                if not str(meta.get(key, "")).strip():
                    raise FieldError(f"{prov.name}: provenance lacks {key}")
            weights = d / meta["file"]
            if weights.is_file():
                h = hashlib.sha256()
                with weights.open("rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                if h.hexdigest() != meta["sha256"]:
                    raise FieldError(f"{prov.name}: weights on disk do not match the pinned hash")
                meta["_present"] = True
            else:
                meta["_present"] = False
            out[meta["id"]] = meta
        except (OSError, ValueError) as e:
            raise FieldError(f"{prov.name}: unreadable ({type(e).__name__}: {e})")
    return out


def model_identity(root, model):
    """The string the verdict records for a model: identifier and parameter scale, from the
    pin — never free text (REQ-8.2, 8.5). 'none' is the no-model configuration (REQ-8.1)."""
    if model in (NO_MODEL, "", None):
        return "none — mechanical only, checklist not applied"
    pins = models(root)
    if model not in pins:
        raise FieldError(f"model '{model}' is not pinned under {MODELS_DIR}/ with provenance; model weights are vendored data")
    m = pins[model]
    return f"{m['id']} {m['version']} ({m['parameters']}; sha256:{m['sha256'][:12]})"


def clear(root):
    """Setting the mode back. Discharges nothing: the obligations remain (REQ-2.5)."""
    p = pathlib.Path(root) / DECLARATION
    if p.is_file():
        p.unlink()
    return len(open_obligations(root))


def run(root, cfg, unit, run_no, base, head, attested_by, model=NO_MODEL, reviewer_class="automated",
        checklist_answers=None, clock=time.monotonic):
    """A field gate run. Returns (summary dict, gate-log line)."""
    decl = declaration(root)
    if not decl:
        raise FieldError("no field-mode declaration; field mode is never inferred")
    model_id = model_identity(root, model)
    if checklist_answers is not None and model in (NO_MODEL, "", None):
        raise FieldError("checklist answers were given but no model or reviewer is named; say what the reviewer is")
    budget = decl["budget_seconds"]
    range_ = f"{base[:12]}..{head[:12]}"
    # REQ-6.4: the started marker first — a run interrupted by the incident still leaves its trace
    gatelog.write_started(root, cfg, unit, run_no, range_, head, extra={"mode": "field", "declared_by": decl["declared_by"]})
    start = clock()
    ran, deferred, could_not, failed = [], [], [], []
    outcomes = []

    def elapsed():
        return clock() - start

    # the floor: always, regardless of budget
    for name, fn in FLOOR:
        o = fn(root, cfg)
        outcomes.append(o)
        ran.append((name, o.state.value))
        if o.state is State.COULD_NOT_RUN:
            could_not.append(name)
        elif o.failed:
            failed.append(name)
    # deferrable, in cost order; once the budget is spent everything remaining is deferred by name
    for name, fn in DEFERRABLE:
        if elapsed() > budget:
            o = Outcome.deferred(name, "budget", f"budget of {budget}s exhausted after {elapsed():.0f}s")
            outcomes.append(o)
            deferred.append(name)
            continue
        if fn is None:
            o = Outcome.deferred(name, "not run on field hardware", "requires the full environment; owed at reconciliation")
            outcomes.append(o)
            deferred.append(name)
            continue
        o = fn(root, cfg)
        outcomes.append(o)
        ran.append((name, o.state.value))
        if o.state is State.COULD_NOT_RUN:
            could_not.append(name)
        elif o.failed:
            failed.append(name)
    # checklist items the model did not reach are deferred, not dropped (REQ-8.4)
    unreached = []
    if checklist_answers is not None:
        for group, i, text, detail, std in checklist.compose(cfg):
            if i not in checklist_answers:
                unreached.append(i)
        if unreached:
            deferred.append("checklist:" + ",".join(unreached))
    total = elapsed()
    verdict = "field-fail" if (failed or could_not) else "field-pass"
    # the obligation: durable, countable, aged
    ob_id = f"OB-{unit}-{run_no}"
    if deferred and (pathlib.Path(root) / OBLIGATIONS).is_file():
        table.append(root, OBLIGATIONS, sch.OBLIGATIONS, {
            "id": ob_id, "opened": now(cfg), "unit": unit, "range": range_, "deferred_checks": ", ".join(deferred),
            "declared_by": decl["declared_by"], "reason": decl["reason"], "status": "open", "discharged_by_run": "-",
            "side": cfg.side if cfg else sch.UNKNOWN})
    boundary = (f"This is a FIELD verdict, not an ordinary gate pass: {len(ran)} check(s) ran, {len(deferred)} were deferred "
                f"({', '.join(deferred) or 'none'}) and are owed under obligation {ob_id if deferred else '(none)'}; "
                f"separation of duties was not achieved; declared by {decl['declared_by']} because {decl['reason']}.")
    problems = failed + could_not
    line = gatelog.append(root, cfg, unit=unit, range=range_, run=str(run_no), mode="field", verdict=verdict,
                          findings="0" if not problems else f"{len(problems)}: " + ", ".join(problems),
                          reviewer=("field-reviewer" if checklist_answers is not None else "mechanical-only"), reviewer_class=reviewer_class,
                          model=model_id, attested_by=attested_by, harness_version=version(), checklist_version=checklist.version(),
                          deferred=", ".join(deferred) or "-", obligation=ob_id if deferred else "-")
    doc = {"mode": "field", "declared": decl, "range": range_, "checks_run": ran, "checks_deferred": deferred,
           "could_not_run": could_not, "did_not_run_in_time": [o.check for o in outcomes if o.state is State.DEFERRED and o.reason == "budget"],
           "separation_of_duties": "not achieved", "reviewer_class": reviewer_class, "model": model_id,
           "reconciliation": "open" if deferred else "none owed", "budget_seconds": budget, "elapsed_seconds": round(total, 1),
           "completed_within_budget": not any(o.state is State.DEFERRED and o.reason == "budget" for o in outcomes),
           "boundary": boundary, "verdict": verdict, "obligation": ob_id if deferred else None}
    p = pathlib.Path(root) / ".engine" / "work" / f"field-verdict-{unit}-{run_no}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(doc, outcomes), encoding="utf-8", newline="\n")
    return doc, line, outcomes


def render(doc, outcomes):
    L = [f"# FIELD VERDICT — {doc['range']}", "", doc["boundary"], "",
         f"mode: field; declared by {doc['declared']['declared_by']} at {doc['declared']['declared_at']}; reason: {doc['declared']['reason']}; "
         f"impossible: {doc['declared']['impossible']}",
         f"verdict: {doc['verdict']}; separation of duties: {doc['separation_of_duties']}; reviewer class: {doc['reviewer_class']}; model: {doc['model']}",
         f"budget: {doc['budget_seconds']}s; elapsed: {doc['elapsed_seconds']}s; "
         + ("completed everything inside the budget" if doc["completed_within_budget"] else "budget exhausted — deferrals below"),
         f"reconciliation: {doc['reconciliation']}" + (f" ({doc['obligation']})" if doc["obligation"] else ""), "", "## Checks run", ""]
    L += [f"- {n}: {s}" for n, s in doc["checks_run"]]
    L += ["", "## Checks deferred (owed)", ""] + ([f"- {d}" for d in doc["checks_deferred"]] or ["(none)"])
    L += ["", "## Could not run (a different state from deferred)", ""] + ([f"- {c}" for c in doc["could_not_run"]] or ["(none)"])
    L += ["", "## Outcome lines", ""] + [o.line() for o in outcomes]
    L += ["", "## What field mode changes", ""] + [f"- {a}: {b}" for a, b in DEGRADATION_TABLE]
    return "\n".join(L) + "\n"


def reconcile(root, cfg, obligation_id, run_no, attested_by, checks_run):
    """Discharge an obligation with a full re-gate that specifically confirmed every deferred
    item. `checks_run` is {check name: passed}. Anything deferred and not confirmed leaves the
    obligation open. Produces its own gate-log row referencing the field row."""
    rows, _, _ = table.read(root, OBLIGATIONS, "reconciliation-obligations")
    latest = {r["id"]: r for r in (rows or [])}
    ob = latest.get(obligation_id)
    if not ob or ob["status"] != "open":
        raise FieldError(f"no open obligation {obligation_id}")
    owed = [x.strip() for x in ob["deferred_checks"].split(",") if x.strip()]
    missing = [x for x in owed if not checks_run.get(x)]
    if missing:
        raise FieldError(f"reconciliation must specifically confirm every deferred item; not confirmed: {', '.join(missing)}")
    values = {c: ob[c] for c in sch.OBLIGATIONS[2]}
    values.update({"status": "discharged", "discharged_by_run": f"{ob['unit']}#{run_no}", "side": cfg.side if cfg else sch.UNKNOWN})
    table.append(root, OBLIGATIONS, sch.OBLIGATIONS, values)
    field_run = obligation_id.split("-")[-1]
    line = gatelog.append(root, cfg, unit=ob["unit"], range=ob["range"], run=str(run_no), verdict="pass",
                          findings="0", reviewer="reconciliation", reviewer_class="automated-with-human-review", model="-",
                          attested_by=attested_by, harness_version=version(), checklist_version=checklist.version(),
                          tickets=f"discharges {obligation_id} (field run {ob['unit']}#{field_run})", obligation=obligation_id)
    return line


def report(root, cfg):
    """The lines every gate and every export carry (REQ-7.2, 7.5, 7.7)."""
    open_ = open_obligations(root)
    aged = aged_obligations(root, cfg)
    lines = [f"reconciliation obligations open: {len(open_)}" + (f" ({', '.join(r['id'] for r in open_)})" if open_ else "")]
    for ident, age in aged:
        lines.append(f"FINDING: obligation {ident} is {age} day(s) old, past the threshold — a field posture is becoming permanent")
    return lines, len(open_), aged
