# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The control manifest (spec 01 §7): the project's declarative register of its
security controls, and the verifier that recomputes what is true and compares.

The manifest declares what *should* be true — identifier, description,
implementation location, required artifact, proving-test pattern, and the
implementation status in the assessment vocabulary (system-specific or hybrid,
with the shared-responsibility counterpart for hybrid; inherited controls are
not present and are covered by the scope statement). Call sites are never
stored: they are recomputed from the tree on every run, so the manifest cannot
go stale in the direction that matters.

Verification distinguishes three states: every entry resolves; at least one
fails; the manifest holds only template placeholders.
"""
import fnmatch
import json
import pathlib
import re

from . import gitutil
from .controlshape import SOURCE_EXT, TEST_PATH

FILE = ".engine/rules/control-manifest.json"
SCOPE_STATEMENT = ("This manifest covers system-specific controls and the system-specific portion of hybrid controls. "
                   "Fully inherited controls are implemented by the hosting platform, are tracked in the platform's "
                   "system security plan, and are outside this harness's verification scope.")
STATUSES = ("system-specific", "hybrid")
FORBIDDEN_KEYS = ("call_sites", "callsites", "callers")


class ManifestError(Exception):
    pass


def load(root):
    p = pathlib.Path(root) / FILE
    if not p.is_file():
        raise ManifestError(f"{FILE} does not exist")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ManifestError(f"{FILE} is not valid JSON: {e}")
    return data


def problems(data):
    """Structural problems with the manifest, in words."""
    out = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]
    if data.get("scope_statement", "").strip() != SCOPE_STATEMENT:
        out.append("scope statement is missing or differs from the required text")
    controls = data.get("controls")
    if not isinstance(controls, list):
        return out + ["'controls' must be a list"]
    seen = set()
    for i, c in enumerate(controls):
        tag = c.get("id", f"#{i}") if isinstance(c, dict) else f"#{i}"
        if not isinstance(c, dict):
            out.append(f"{tag}: entry is not an object")
            continue
        for key in ("id", "description", "location", "test_pattern", "status"):
            if key not in c:
                out.append(f"{tag}: missing '{key}'")
        if tag in seen:
            out.append(f"{tag}: duplicate identifier")
        seen.add(tag)
        loc = c.get("location")
        if not isinstance(loc, dict) or not loc.get("file") or not loc.get("symbol"):
            out.append(f"{tag}: location must name a file and a symbol")
        st = c.get("status")
        if st == "inherited":
            out.append(f"{tag}: inherited controls are not present in the manifest; they are covered by the scope statement")
        elif st not in STATUSES:
            out.append(f"{tag}: status must be one of {STATUSES}")
        if st == "hybrid" and not (c.get("counterpart") or "").strip():
            out.append(f"{tag}: a hybrid control names its shared-responsibility counterpart")
        for k in FORBIDDEN_KEYS:
            if k in c:
                out.append(f"{tag}: call sites are recomputed on every run, never stored ('{k}')")
        branches = c.get("branches")
        if branches is not None and (not isinstance(branches, list) or not all(isinstance(b, dict) and b.get("name") for b in branches)):
            out.append(f"{tag}: branches must be a list of objects with a name")
        mut = c.get("mutation")
        if isinstance(branches, list) and len(branches) > 1 and mut and not mut.get("rationale"):
            out.append(f"{tag}: a single mutation for a multi-branch control must state why it is representative")
    return out


def real_controls(data):
    return [c for c in data.get("controls", []) if isinstance(c, dict) and not c.get("placeholder")]


def is_template_only(data):
    return len(real_controls(data)) == 0


# --- recomputation from the tree ---

def _source_files(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [f for f in files if pathlib.Path(f).suffix in SOURCE_EXT and not f.startswith(".engine/")]


DEF_LINE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|class|const|let|var|fun|func|val)\s+{sym}\b|"
                      r"^\s*(?:public|private|protected|static|\s)*[\w<>\[\]]+\s+{sym}\s*\(")
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|<!--)")


def definition_line(text, symbol):
    pat = re.compile(DEF_LINE.pattern.replace("{sym}", re.escape(symbol)))
    for n, line in enumerate(text.splitlines(), 1):
        if pat.match(line):
            return n
    return None


def call_sites(root, symbol, definition_file):
    """Production call sites of `symbol`, recomputed: every non-comment mention in
    a non-test source file, excluding the definition line. Indirect invocation —
    the symbol passed by reference, used as a decorator, or registered — counts. A
    handler registered by a decorator directly above its definition (`@app.route(...)`
    then `def handler`) is mentioned nowhere else: the decorator line is its
    registration and counts as its production site."""
    root = pathlib.Path(root)
    # a preceding dot is an attribute call (`principals.principal_for(...)`), the way every method is
    # called; excluding it made a control that is a method uncallable in the verifier's eyes
    mention = re.compile(r"(?<!\w)" + re.escape(symbol) + r"(?![\w])")
    out = []
    for rel in _source_files(root):
        if TEST_PATH.search(rel):
            continue
        p = root / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        def_line = definition_line(text, symbol) if rel == definition_file else None
        if def_line:
            n = def_line - 1
            while n >= 1 and lines[n - 1].strip().startswith("@"):
                out.append(f"{rel}:{n}")
                n -= 1
        for n, line in enumerate(lines, 1):
            if n == def_line or COMMENT.match(line):
                continue
            stripped = re.sub(r"(#|//).*$", "", line)
            if mention.search(stripped) and not re.match(r"^\s*(import|from)\b", stripped):
                out.append(f"{rel}:{n}")
    return out


def matching_tests(root, pattern):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [f for f in files if fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(pathlib.Path(f).name, pattern)]


def verify_entry(root, c):
    """Problems for one entry (empty when it resolves) and the recomputed facts."""
    root = pathlib.Path(root)
    probs, facts = [], {}
    loc = c["location"]
    p = root / loc["file"]
    if not p.is_file():
        probs.append(f"implementation file {loc['file']} does not exist")
        return probs, facts
    text = p.read_text(encoding="utf-8", errors="replace")
    d = definition_line(text, loc["symbol"])
    if d is None:
        probs.append(f"symbol {loc['symbol']} is not defined in {loc['file']}")
    facts["definition_line"] = d
    sites = call_sites(root, loc["symbol"], loc["file"])
    facts["call_sites"] = sites
    if not sites:
        probs.append(f"{loc['symbol']} has no production call site (recomputed; definition and tests excluded)")
    art = c.get("required_artifact")
    if art:
        facts["artifact_present"] = (root / art).exists()
        if not facts["artifact_present"]:
            probs.append(f"required artifact {art} is absent")
    tests = matching_tests(root, c["test_pattern"])
    facts["tests"] = tests
    if not tests:
        probs.append(f"no test matches {c['test_pattern']}")
    return probs, facts


def verify(root):
    """Returns (state, per-entry results, structural problems).
    state ∈ {'resolved', 'failed', 'template-only', 'invalid'}."""
    data = load(root)
    structural = problems(data)
    if structural:
        return "invalid", [], structural
    controls = real_controls(data)
    if not controls:
        return "template-only", [], []
    results = []
    for c in controls:
        probs, facts = verify_entry(root, c)
        results.append({"id": c["id"], "status": c["status"], "counterpart": c.get("counterpart"),
                        "problems": probs, "facts": facts})
    state = "failed" if any(r["problems"] for r in results) else "resolved"
    return state, results, []
