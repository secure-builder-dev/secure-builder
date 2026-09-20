# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Generated system truth (spec 02 §9; spec 03 REQ-3.5.3).

An inventory of the system's actual interfaces and data structures, generated
from the code itself and regenerated — never hand-edited. It is compared with
the planned design; each divergence is a human decision (revise the plan, or
open a ticket) and is never silently reconciled in either direction. The route
inventory is the input to the negative-test enumeration, so its accuracy is
load-bearing for a control, not documentation.
"""
import hashlib
import pathlib
import re

from . import gitutil, lifecycle, routes
from .controlshape import TEST_PATH
from .outcome import Outcome

FILE = ".engine/records/generated-truth.md"
PLAN = "plans/design.md"
MARKER = "GENERATED from the code by the harness — never hand-edited; regenerate with `engine truth`"
STRUCTURE = [
    ("py-class", re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b", re.M)),
    ("ts-interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_]\w*)\b", re.M)),
    ("ts-type", re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_]\w*)\s*=", re.M)),
    ("sql-table", re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?([A-Za-z_]\w*)", re.I)),
    ("kotlin-data", re.compile(r"^\s*data\s+class\s+([A-Za-z_]\w*)\b", re.M)),
]
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".kt", ".java", ".sql", ".prisma"}


def structures(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    out = []
    for f in files:
        if pathlib.Path(f).suffix not in SOURCE_EXT or TEST_PATH.search(f) or f.startswith((".engine/", "engine/", "selftest/", "tools/", "hooks/", "integration/")):
            continue
        p = root / f
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for kind, pat in STRUCTURE:
            for m in pat.finditer(text):
                out.append({"name": m.group(1), "kind": kind, "file": f, "line": text.count("\n", 0, m.start()) + 1})
    return out


def generate(root):
    return {"routes": routes.inventory(root), "structures": structures(root)}


def render(truth):
    L = ["# Generated system truth", "", MARKER, "", "## Interfaces", ""]
    L += [f"- {r['method']} {r['path']} ({r['file']}:{r['line']})" for r in truth["routes"]] or ["(none)"]
    L += ["", "## Data structures", ""]
    L += [f"- {s['name']} [{s['kind']}] ({s['file']}:{s['line']})" for s in truth["structures"]] or ["(none)"]
    body = "\n".join(L) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return body + f"\ncontent: sha256:{digest}\n"


def write(root):
    truth = generate(root)
    text = render(truth)
    p = pathlib.Path(root) / FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return truth


def hand_edited(root):
    """True when the file on disk is not what regeneration produces (someone edited it, or it is stale)."""
    p = pathlib.Path(root) / FILE
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8") != render(generate(root))


def plan(root):
    p = pathlib.Path(root) / PLAN
    if not p.is_file():
        return None
    section, out = None, {"interfaces": set(), "data": set()}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
        elif line.startswith("- ") and section in ("interfaces", "data", "data structures"):
            key = "interfaces" if section == "interfaces" else "data"
            out[key].add(line[2:].strip())
    return out


def divergences(truth, planned):
    actual_routes = {f"{r['method']} {r['path']}" for r in truth["routes"]}
    actual_data = {s["name"] for s in truth["structures"]}
    out = []
    out += [("interface", "in code, not in plan", x) for x in sorted(actual_routes - planned["interfaces"])]
    out += [("interface", "in plan, not in code", x) for x in sorted(planned["interfaces"] - actual_routes)]
    out += [("data", "in code, not in plan", x) for x in sorted(actual_data - planned["data"])]
    out += [("data", "in plan, not in code", x) for x in sorted(planned["data"] - actual_data)]
    return out


def check(root, cfg):
    name = "generated-truth"
    truth = write(root)          # regenerated, never hand-edited
    planned = plan(root)
    if planned is None:
        return Outcome.nothing_yet(name, "a planned design to compare against",
                                   f"{len(truth['routes'])} interface(s) and {len(truth['structures'])} structure(s) generated; no {PLAN}")
    div = divergences(truth, planned)
    if not div:
        return Outcome.clean(name, f"{len(truth['routes'])} interface(s) and {len(truth['structures'])} structure(s) match the plan")
    findings = []
    for kind, direction, item in div:
        ident = "TRUTH-" + re.sub(r"[^A-Za-z0-9]+", "-", f"{kind}-{item}").strip("-")[:60]
        ticket = pathlib.Path(root) / lifecycle.ITEMS_DIR / f"{ident}.md"
        if not ticket.exists():
            lifecycle.create_item(root, ident, "planning", f"The divergence '{item}' ({direction}) is resolved by a recorded decision: the plan is revised or the code is changed.")
        findings.append(f"{kind} {item}: {direction} — a human decision (revise the plan or change the code); ticket {ident}")
    return Outcome.found(name, f"{len(div)} divergence(s) between generated truth and the plan; none reconciled silently", findings, blocking=False)
