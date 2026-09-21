# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Evidence export (spec 02 §10; spec 02 §6.4; spec 04 §6–7; spec 01 REQ-4.9.2).

The harness produces, as exhaust, most of an assessment package. This module
joins it: a control-to-evidence traceability index in the shape of a security
requirements traceability matrix, a dated self-contained bundle bound to the
commit it describes, a manifest whose hashes are computed at export, a
disclosure statement generated from the record set and placed at the front,
the degradation statement, the redacted scan bundle, the composition
inventories, and an index page that renders with no network. Classification
marking is applied uniformly or the export refuses.
"""
import datetime
import hashlib
import json
import pathlib
import re

from . import checklist, degradation, field, gitutil, manifest, mutate, probes, topology, truth, version
from . import config as cfgmod
from .checks import REGISTRY
from .records import findings as findings_mod
from .records import gatelog, table

NL = chr(10)
SCAN_RAW = ".engine/records/scan/raw"
SCAN_SBOM = ".engine/records/scan/sbom"
SCAN_FILES = (".engine/records/scan/actionable.md", ".engine/records/scan/carried.md", ".engine/records/scan/stamp.json")
RECORD_FILES = [
    ("findings-register.md", ".engine/records/findings-register.md"),
    ("governance-changelog.md", ".engine/records/governance-changelog.md"),
    ("standing-state-deltas.md", ".engine/records/standing-state-deltas.md"),
    ("coverage-inventory.md", ".engine/records/coverage-inventory.md"),
    ("plan-of-action.md", ".engine/records/carried-findings.md"),
    ("reconciliation-obligations.md", ".engine/records/reconciliation-obligations.md"),
    ("mutation-results.md", ".engine/records/mutation-results.md"),
    ("generated-truth.md", ".engine/records/generated-truth.md"),
    ("ingest-records.md", ".engine/records/ingest-records.md"),
    ("high-side-changes.md", ".engine/records/high-side-changes.md"),
]
# Artifacts whose content is a deterministic function of the inputs, and those that are not (spec 01 §1.5).
DETERMINISTIC = ("mechanical checks (the registry below)", "control wiring verification (manifest)", "mutation results",
                 "composition inventories", "scan correlation", "generated system truth", "coverage inventory",
                 "standing-state snapshots and deltas", "this traceability index and this disclosure")
NON_DETERMINISTIC = ("security-gate verdicts by an agent reviewer applying the versioned checklist",
                     "quality-gate judgment items", "field-mode reviewer answers")
HUMAN_AUTHORED = ("findings-register dispositions and risk acceptances", "carried-finding owners, milestones and reasons",
                  "governance changes and their sign-off", "attestations on every gate row", "field-mode declarations")


class ExportError(Exception):
    pass


# --- redaction (spec 02 REQ-6.4.2–6.4.3) ---

REDACTIONS = [
    ("digest", re.compile(r"sha256:[0-9a-f]{64}")),
    ("aws-account", re.compile(r"\b\d{12}\b(?=\.dkr\.ecr|:|/)")),
    ("arn", re.compile(r"\barn:[a-z-]+:[a-z0-9-]*:[a-z0-9-]*:\d{12}:[^\s\"',]*")),
    ("registry-path", re.compile(r"\b(?:[a-z0-9-]+\.)+(?:[a-z]{2,})(?::\d+)?/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+(?=[:@\s\"']|$)")),
    ("hostname", re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|io|mil|gov|net|org|local|internal|lan|corp|edu)\b(?::\d+)?")),
    ("home-path", re.compile(r"(?:[A-Za-z]:\\Users\\|/home/|/Users/)[^\\/\s\"']+")),
]


def redact(text):
    """Environment identifiers out; vulnerability identifiers, package names and versions stay."""
    for kind, pat in REDACTIONS:
        text = pat.sub(f"<redacted {kind}>", text)
    return text


def redaction_problems(text):
    """Identifiers a redacted text must not contain — the check the export runs on its own output."""
    return [f"{kind} still present" for kind, pat in REDACTIONS if pat.search(text)]


# --- traceability index (REQ-10.2.1, 10.2.1a, 10.2.1b, 10.2.7) ---

SRTM_COLUMNS = ["Control ID", "Implementation Status", "Responsible Party", "Implementation", "Test Evidence",
                "Developer Testing", "Assessment Records", "Open Findings"]


def traceability(root, cfg):
    """One SRTM row per declared control, joined from the manifest, the code, the mutation
    results, the gate log and the carried findings. Nothing here is typed by hand."""
    state, results, structural = manifest.verify(root)
    if state == "invalid":
        raise ExportError("control manifest is invalid: " + "; ".join(structural))
    data = manifest.load(root)
    controls = manifest.real_controls(data)
    mut_rows, _ = mutate.read_results(root)
    gate_rows, _ = gatelog.series(root)
    carried, _, _ = table.read(root, ".engine/records/carried-findings.md", "carried-findings")
    b_open = [r for r in findings_mod.read(root)[1] if r["status"] == "open"]
    facts = {r["id"]: r for r in results}
    rows = []
    for c in controls:
        cid = c["id"]
        f = facts.get(cid, {"problems": [], "facts": {}})
        loc = c["location"]
        impl = f"{loc['file']}:{loc['symbol']}"
        if f["facts"].get("definition_line"):
            impl += f" (line {f['facts']['definition_line']}; {len(f['facts'].get('call_sites', []))} call site(s))"
        if f["problems"]:
            impl += " — NOT VERIFIED: " + "; ".join(f["problems"])
        tests = f["facts"].get("tests") or []
        muts = [m for m in mut_rows if m["control"] == cid]
        latest = muts[-1] if muts else None
        mut = (f"{latest['result']} ({latest['date']}; baseline {latest['baseline']}; {latest['mutation']})" if latest
               else "no mutation result recorded — the control has not been proven by breaking it")
        assessed = [r for r in gate_rows if not r["_superseded"] and cid in [x.strip() for x in r.get("controls", "").split(",")]]
        gates = ", ".join(f"{r['unit']}#{r['run']} {r['verdict']} ({r['date'][:10]})" for r in assessed) or "no gate run records assessing this control"
        against = [r for r in (carried or []) if cid in " ".join(v for k, v in r.items() if not k.startswith("_")) and r["status"] != "closed"]
        against += [r for r in b_open if cid in " ".join(v for k, v in r.items() if not k.startswith("_"))]
        open_f = ", ".join(sorted({r["id"] for r in against})) or "none recorded"
        status = c["status"]
        party = "system (this codebase)" if status == "system-specific" else f"shared: system + {c.get('counterpart') or 'counterpart NOT NAMED'}"
        rows.append({"Control ID": cid, "Implementation Status": status, "Responsible Party": party, "Implementation": impl,
                     "Test Evidence": ", ".join(tests) or "no matching test", "Developer Testing": mut,
                     "Assessment Records": gates, "Open Findings": open_f, "_description": c.get("description", "")})
    return {"scope_statement": data["scope_statement"], "manifest_state": state, "rows": rows}


def render_traceability(idx, commit):
    L = ["# Control-to-evidence traceability index (SRTM)", "",
         f"commit: {commit}", f"generated: {_now()}", f"manifest verification: {idx['manifest_state']}", "",
         "## Scope", "", idx["scope_statement"], "",
         "## Matrix", "", "| " + " | ".join(SRTM_COLUMNS) + " |", "|" + "---|" * len(SRTM_COLUMNS)]
    for r in idx["rows"]:
        L.append("| " + " | ".join(str(r[c]).replace("|", "/") for c in SRTM_COLUMNS) + " |")
    if not idx["rows"]:
        L.append("| (no controls declared — the manifest is template-only) |" + " |" * (len(SRTM_COLUMNS) - 1))
    return "\n".join(L) + "\n"


# --- implementation narrative (REQ-10.2.6) ---

def narrative(root, idx):
    root = pathlib.Path(root)
    L = ["# Implementation narrative", "", "Generated from the control manifest and the code; regenerate rather than edit.", ""]
    for r in idx["rows"]:
        file_, _, symbol = r["Implementation"].partition(":")
        symbol = symbol.split(" ")[0]
        doc = _symbol_doc(root / file_, symbol)
        L += [f"## {r['Control ID']}", "",
              f"{r['Control ID']} is a {r['Implementation Status']} control ({r['Responsible Party']}). "
              f"It is implemented by `{symbol}` in `{file_}`. " + (f"The code describes it as: \"{doc}\" " if doc else "")
              + f"It is exercised by {r['Test Evidence']}. Developer security testing: {r['Developer Testing']}. "
              f"Assessment records: {r['Assessment Records']}. Open findings: {r['Open Findings']}.", ""]
        if r["_description"]:
            L += [f"Declared purpose: {r['_description']}", ""]
    if not idx["rows"]:
        L.append("(no controls declared)")
    return "\n".join(L) + "\n"


def _symbol_doc(path, symbol):
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    d = manifest.definition_line(text, symbol)
    if d is None:
        return ""
    lines = text.splitlines()
    for line in lines[d:d + 3]:
        s = line.strip()
        m = re.match(r"^(?:\"\"\"|''')(.*?)(?:\"\"\"|''')?$", s) or re.match(r"^(?://|#|/\*\*?|\*)\s*(.+)$", s)
        if m and m.group(1).strip():
            return m.group(1).strip().rstrip("*/").strip()
    return ""


# --- disclosure (REQ-10.5.1–10.5.4; spec 01 REQ-1.5.2) ---

def disclosure(root, cfg, commit):
    """Generated from the record set, never hand-maintained."""
    rows, _ = gatelog.series(root)
    live = [r for r in rows if not r["_superseded"]]
    attesters = sorted({r["attested_by"] for r in live if r["attested_by"] not in ("", "unknown", "-")})
    classes = sorted({r["reviewer_class"] for r in live})
    models = sorted({r["model"] for r in live if r["model"] not in ("", "-", "unknown")})
    cl_versions = sorted({r["checklist_version"] for r in live if r["checklist_version"] not in ("", "unknown")})
    hv = sorted({r["harness_version"] for r in live if r["harness_version"] not in ("", "unknown")})
    field_rows = [r for r in live if r["mode"] == "field"]
    try:
        ob_lines, n_open, aged = field.report(root, cfg)
    except field.FieldError as e:
        ob_lines = [f"reconciliation obligations: NOT COUNTABLE ({e})"]
    L = ["# Disclosure statement", "", f"commit: {commit}", f"generated: {_now()} from the record set by harness {version()}", "",
         "## How this evidence was produced", "",
         "The gates are automated reviewers applying a versioned checklist; every verdict row names its checklist version, "
         "its reviewer class, the model where one performed the review, and the human who attested the unit of work. "
         f"Gate rows in this package: {len(live)} live ({len(rows) - len(live)} superseded, retained). "
         f"Field-mode rows: {len(field_rows)}. {ob_lines[0]}.", "",
         f"- checklist versions applied: {', '.join(cl_versions) or 'none recorded'}",
         f"- harness versions: {', '.join(hv) or 'none recorded'}; this export: {version()}",
         f"- reviewer classes seen: {', '.join(classes) or 'none recorded'}",
         f"- models named: {', '.join(models) or 'none recorded'}",
         f"- attested by: {', '.join(attesters) or 'NO ATTESTATION RECORDED'}", "",
         "## Deterministic artifacts (reproducible from the inputs; implemented as mechanical checks, never left to a reviewing agent)", ""]
    L += [f"- {d}" for d in DETERMINISTIC]
    L += ["", "mechanical check registry: " + ", ".join(REGISTRY), "",
          "## Non-deterministic artifacts (an agent's judgment; weight them by the recorded reviewer and model)", ""]
    L += [f"- {d}" for d in NON_DETERMINISTIC]
    L += ["", f"checklist version at export: {checklist.version()}", "", "## Human-authored artifacts", ""]
    L += [f"- {d}" for d in HUMAN_AUTHORED]
    L += ["", "## Topology", "", f"side: {cfg.side}; topology: {cfg.topology}"]
    L += [f"- {line}" for line in topology.report(root, cfg)]
    if cfg.side == "high":
        L.append("- this record set is the deliverable one for anything assessed against the high-side system (spec 04 REQ-10.1.5); "
                 "it was produced without any return path from the high side")
    L += ["", "## Machine-generated artifacts in this bundle", "",
          "traceability index, implementation narrative, degradation statement, coverage inventory, generated truth, "
          "composition inventories, redacted scan bundle, this statement, the manifest with its hashes.", ""]
    for line in ob_lines[1:]:
        L.append(f"- {line}")
    return "\n".join(L) + "\n"


# --- retention (REQ-10.4.1–10.4.2) ---

def retention(cfg, today):
    r = cfg.get("retention") or {}
    try:
        auth, audit = int(r.get("authorization_period_years")), int(r.get("audit_retention_years"))
    except (TypeError, ValueError):
        return {"configured": False, "statement": "retention NOT CONFIGURED — set retention.authorization_period_years and "
                                                   "retention.audit_retention_years to the baseline's values; the records are plain text in "
                                                   "version control and outlive the harness regardless"}
    until = today.replace(year=today.year + auth + audit)
    return {"configured": True, "years": auth + audit, "retain_until": until.isoformat(),
            "statement": f"retain at least {auth + audit} years from {today.isoformat()} (authorization period {auth} + audit retention {audit}): "
                         f"until {until.isoformat()}. Records are plain text in version control; retention does not depend on the harness."}


# --- offline rendering (spec 04 §6) ---

FETCH = re.compile(r"""(?i)(?:src|href|@import|url\()\s*=?\s*["'(]?\s*(?:https?:)?//""")
DIAGRAM = ('<svg viewBox="0 0 640 120" width="640" height="120" role="img" aria-label="evidence flow">'
           '<rect x="8" y="30" width="150" height="60" fill="none" stroke="currentColor"/><text x="83" y="65" text-anchor="middle">code + manifest</text>'
           '<path d="M158 60 H238" stroke="currentColor" marker-end="url(#a)"/>'
           '<rect x="240" y="30" width="150" height="60" fill="none" stroke="currentColor"/><text x="315" y="65" text-anchor="middle">gates + records</text>'
           '<path d="M390 60 H470" stroke="currentColor"/>'
           '<rect x="472" y="30" width="160" height="60" fill="none" stroke="currentColor"/><text x="552" y="65" text-anchor="middle">this package</text>'
           '<defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs></svg>')


def render_index(entries, commit, marking):
    """A page that renders with no network: system fonts, inline vector diagram, nothing fetched."""
    rows = "".join(f'<tr><td><a href="{e["path"]}">{e["path"]}</a></td><td>{e["kind"]}</td><td><code>{e["sha256"][:16]}</code></td></tr>' for e in entries)
    banner = f'<p class="marking">{marking}</p>' if marking else ""
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Evidence package " + commit[:12] + "</title>"
            "<style>body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;max-width:60em;margin:2em auto;padding:0 1em}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #888;padding:.3em .5em;text-align:left}"
            ".marking{text-align:center;font-weight:bold;border:2px solid currentColor;padding:.3em}</style></head><body>"
            + banner + f"<h1>Evidence package — commit {commit}</h1><p>Read <a href=\"00-DISCLOSURE.md\">the disclosure statement</a> first.</p>"
            + DIAGRAM + "<table><tr><th>artifact</th><th>kind</th><th>sha256 (prefix)</th></tr>" + rows + "</table>" + banner + "</body></html>\n")


def offline_problems(html):
    out = []
    if FETCH.search(html):
        out.append("the page fetches a resource from a network location at render time")
    if "<script" in html.lower():
        out.append("the page carries a script; generated pages render without one")
    if "font-family" in html and "system-ui" not in html and "@font-face" not in html:
        out.append("typeface is neither embedded nor degrading to system fonts")
    if "<img" in html.lower() and "data:" not in html.lower():
        out.append("an image is referenced by location rather than inlined")
    return out


# --- scan bundle (spec 02 REQ-6.4.1–6.4.3) ---

def mark(rel, text, marking):
    """Marking applied uniformly: a banner at the top and bottom of every text page; a
    top-level field in every JSON document (a banner would break the document)."""
    if not marking:
        return text
    if rel.endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            return json.dumps({"_classification_marking": marking, **data}, indent=2, sort_keys=False) + NL
        return json.dumps({"_classification_marking": marking, "content": data}, indent=2) + NL
    if rel.endswith(".html"):
        return text
    return f"{marking}{NL}{NL}{text.rstrip()}{NL}{NL}{marking}{NL}"


def scan_bundle(root, out_dir, cfg, redacted=True, marking=None):
    """Copy the scan artifacts into a dated bundle, redacted for crossing a boundary."""
    root = pathlib.Path(root)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    sources = []
    for d in (SCAN_RAW, SCAN_SBOM):
        if (root / d).is_dir():
            sources += sorted(p for p in (root / d).rglob("*") if p.is_file())
    sources += [root / f for f in SCAN_FILES if (root / f).is_file()]
    for p in sources:
        rel = p.relative_to(root / ".engine" / "records" / "scan").as_posix()
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = p.read_text(encoding="utf-8", errors="replace")
        if redacted:
            text = redact(text)
            probs = redaction_problems(text)
            if probs:
                raise ExportError(f"{rel}: redaction incomplete — " + "; ".join(probs))
        dest.write_text(mark(rel, text, marking), encoding="utf-8", newline="\n")
        entries.append({"path": rel, "sha256": _sha256(dest), "redacted": redacted})
    meta = {"kind": "scan-bundle", "date": _now(), "redacted": redacted, "marking": marking, "side": cfg.side if cfg else "unknown",
            "detection_data_date": _read(root / ".engine/records/scan/detection-data-date"), "files": entries}
    (out / "BUNDLE.json").write_text(mark("BUNDLE.json", json.dumps(meta, indent=2, sort_keys=True) + NL, marking), encoding="utf-8", newline=NL)
    return meta


# --- the package (REQ-10.2.2–10.2.5, 10.3.3; spec 04 REQ-7.2; spec 01 REQ-4.9.2) ---

def package(root, cfg, out_dir, marking=None):
    root = pathlib.Path(root)
    if not gitutil.is_repo(root):
        raise ExportError("the export describes a commit; this is not a git repository")
    commit = gitutil.head(root)
    if not commit:
        raise ExportError("no commit to bind the package to")
    marking = marking if marking is not None else cfg.get("classification_marking")
    if cfg.get("marking_required") and not (marking or "").strip():
        raise ExportError("classification marking is required by configuration and not configured; export refused")
    marking = (marking or "").strip() or None
    today = datetime.date.today()
    out = pathlib.Path(out_dir) / f"evidence-{today.isoformat()}-{commit[:12]}"
    if out.exists():
        raise ExportError(f"{out} already exists; an export is never overwritten")
    out.mkdir(parents=True)
    entries = []

    def put(rel, text, kind):
        text = mark(rel, text, marking)
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        entries.append({"path": rel, "kind": kind, "sha256": _sha256(p)})

    problems = []
    put("00-DISCLOSURE.md", disclosure(root, cfg, commit), "disclosure statement (generated)")
    idx = traceability(root, cfg)
    put("01-traceability-index.md", render_traceability(idx, commit), "control-to-evidence traceability index (SRTM shape)")
    put("02-implementation-narrative.md", narrative(root, idx), "implementation narrative (generated)")
    try:
        put("03-degradation-statement.md", degradation.statement(root), "degradation statement (spec 04 §7)")
    except cfgmod.ConfigError as e:
        problems.append(f"degradation statement: {e}")
    put("04-record-authority.md", topology.render_authority(cfg), "record authority and what crosses (spec 04 §10.1–10.2)")
    if (root / topology.RECEIVED).is_file():
        put("records/received-drops.json", (root / topology.RECEIVED).read_text(encoding="utf-8"), "received source drops")
    for i, p in enumerate(gatelog.series_files(root)):
        put(f"gate-log/{p.name}", p.read_text(encoding="utf-8"), "gate log series")
    if not gatelog.series_files(root):
        problems.append("no gate log series")
    probes.write_inventory(root, cfg)      # the assessed boundary, regenerated at export
    truth.write(root)                      # the generated system truth, regenerated at export
    for name, rel in RECORD_FILES:
        p = root / rel
        if p.is_file():
            put(f"records/{name}", p.read_text(encoding="utf-8"), "record (append-only, plain text)")
        else:
            problems.append(f"record absent: {rel}")
    sboms = sorted((root / SCAN_SBOM).glob("*.json")) if (root / SCAN_SBOM).is_dir() else []
    for p in sboms:
        put(f"sbom/{p.name}", p.read_text(encoding="utf-8", errors="replace"), "composition inventory (SBOM)")
    if not sboms:
        problems.append("no composition inventory for any shipped image (spec 01 §4.9)")
    if (root / ".engine" / "records" / "scan").is_dir():
        meta = scan_bundle(root, out / "scan", cfg, redacted=True, marking=marking)
        for f in meta["files"]:
            entries.append({"path": f"scan/{f['path']}", "kind": "scan artifact (redacted)", "sha256": f["sha256"]})
        entries.append({"path": "scan/BUNDLE.json", "kind": "scan bundle manifest", "sha256": _sha256(out / "scan" / "BUNDLE.json")})
    else:
        problems.append("no scan artifacts")
    ret = retention(cfg, today)
    put("RETENTION.md", "# Retention\n\n" + ret["statement"] + "\n", "retention statement")
    if not ret["configured"]:
        problems.append("retention period not configured")
    html = render_index(entries, commit, marking)
    off = offline_problems(html)
    if off:
        raise ExportError("index page would not render offline: " + "; ".join(off))
    (out / "index.html").write_text(html, encoding="utf-8", newline="\n")
    entries.append({"path": "index.html", "kind": "index page (renders offline)", "sha256": _sha256(out / "index.html")})
    manifest_doc = {"kind": "evidence-package", "commit": commit, "date": today.isoformat(), "generated": _now(),
                    "harness_version": version(), "marking": marking, "_classification_marking": marking, "side": cfg.side, "mode": cfg.mode,
                    "retention": ret, "incomplete": problems, "files": entries,
                    "note": "hashes are computed at export from the files as written; verify with `engine export verify`"}
    (out / "MANIFEST.json").write_text(json.dumps(manifest_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return out, manifest_doc


def verify(package_dir):
    """Recompute every hash in the manifest. Returns (ok, problems)."""
    d = pathlib.Path(package_dir)
    try:
        m = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, [f"MANIFEST.json unreadable: {e}"]
    probs = []
    for e in m.get("files", []):
        p = d / e["path"]
        if not p.is_file():
            probs.append(f"{e['path']}: missing")
        elif _sha256(p) != e["sha256"]:
            probs.append(f"{e['path']}: content differs from the manifest hash")
    listed = {e["path"] for e in m.get("files", [])}
    for p in d.rglob("*"):
        if p.is_file() and p.name != "MANIFEST.json" and p.relative_to(d).as_posix() not in listed:
            probs.append(f"{p.relative_to(d).as_posix()}: present but not in the manifest")
    if not m.get("commit"):
        probs.append("manifest records no commit")
    return not probs, probs


def _sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def _read(p):
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
