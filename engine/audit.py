# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The standing self-test audit (spec 05 §10).

Eight questions, answered mechanically where a pattern can find the defect and
listed for a person where it cannot. Findings from this audit are findings and
follow the ordinary disposition rule: each becomes a check or a checklist line.
The audit reports; it does not block. An audit that finds no test files at all
is a failed audit, not a clean one.
"""
import pathlib
import re

FAILING_STATE = re.compile(r"State\.(FINDINGS|COULD_NOT_RUN)|FINDINGS BLOCKING|COULD NOT RUN|REFUSED|assertNotEqual\(code, 0\)")
IMPRECISE = re.compile(r"assertNotEqual\(\s*\w+,\s*0\s*\)|assertTrue\(\s*(rc|code|res\.returncode)\s*\)|returncode\s*!=\s*0\)")
WHOLE_OUTPUT = re.compile(r"assertIn\([^,]+,\s*(text|out|output|stdout|[^,]*\.join\([^)]*\)|[\w.]+\.getvalue\(\))\s*[,)]")
STRING_LITERAL = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'")
SKIP = re.compile(r"@unittest\.skip|unittest\.skipIf|unittest\.skipUnless|self\.skipTest")
DISCOVERY = re.compile(r"\.(glob|rglob|iterdir)\(|ls-files|splitlines\(\)")
EMPTY_GUARD = re.compile(r"could_not_run\(|nothing_yet\(|not_applicable\(|nothing to|is not a pass|== 0:")
TOOL_CALL = re.compile(r"run_tool\(\s*[\"']([\w.-]+)[\"']")


def _read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def test_files(root):
    out = []
    for p in sorted(pathlib.Path(root).rglob("*.py")):
        if any(part in ("__pycache__", ".git", ".engine") for part in p.parts):
            continue
        if p.name.startswith("test_") or p.name.endswith("_test.py"):
            out.append(p)
    return out


def automated_paths_text(root):
    """Everything that could invoke a test file: CI, scripts, hooks, the check command."""
    root = pathlib.Path(root)
    chunks = []
    for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml", "*.sh", "hooks/*", "Makefile", "engine/__main__.py"):
        for p in root.glob(pattern):
            if p.is_file():
                chunks.append(_read(p))
    return "\n".join(chunks)


def q1_dormant_tests(root):
    """Test files not referenced by any automated path."""
    root = pathlib.Path(root)
    auto = automated_paths_text(root)
    out = []
    for p in test_files(root):
        rel = p.relative_to(root).as_posix()
        if rel.startswith("selftest/") and re.match(r"test_.*\.py$", p.name):
            continue      # discovered by the check command's pattern
        if rel.startswith("integration/"):
            continue      # the integration tier runs these by discovery
        if p.name not in auto and rel not in auto:
            out.append(f"{rel}: no CI workflow, script or hook invokes it")
    return out


def q2_checks_without_negative_fixture(root, registry):
    root = pathlib.Path(root)
    tests = [_read(p) for p in (root / "selftest").glob("test_*.py")] if (root / "selftest").is_dir() else []
    out = []
    for name in registry:
        tokens = (f"{name}.run(", f"checks.{name}", f"{name}.check(", f"cfgmod.check(" if name == "config" else "\0")
        proven = any(any(t in text for t in tokens) and FAILING_STATE.search(text) for text in tests)
        if not proven:
            out.append(f"check '{name}': no self-test exercises it against an input that makes it fail")
    return out


def q3_loops_without_empty_guard(root):
    root = pathlib.Path(root)
    out = []
    for p in sorted((root / "engine" / "checks").glob("*.py")) if (root / "engine" / "checks").is_dir() else []:
        if p.name == "__init__.py":
            continue
        text = _read(p)
        if DISCOVERY.search(text) and not EMPTY_GUARD.search(text):
            out.append(f"{p.relative_to(root).as_posix()}: iterates over a discovered set with no named empty case")
    return out


def _code_lines(text):
    """(lineno, line) for lines outside triple-quoted string literals."""
    inside = False
    for n, line in enumerate(text.splitlines(), 1):
        quotes = line.count('"""') + line.count("'''")
        if inside:
            if quotes % 2 == 1:
                inside = False
            continue
        if quotes % 2 == 1:
            inside = True
            continue
        yield n, line


def _grep(root, files, pattern, label):
    out = []
    for p in files:
        for n, line in _code_lines(_read(p)):
            if pattern.search(STRING_LITERAL.sub('""', line)):
                out.append(f"{p.relative_to(root).as_posix()}:{n}: {label}: {line.strip()[:90]}")
    return out


def q4_imprecise_assertions(root):
    return _grep(root, test_files(root), IMPRECISE, "asserts a class of values")


def q5_whole_output_assertions(root):
    return _grep(root, test_files(root), WHOLE_OUTPUT, "searches whole output")


def q6_environment_dependent_tests(root):
    return _grep(root, test_files(root), SKIP, "skips on environment")


def q7_sequences_continuing_past_failure(root):
    root = pathlib.Path(root)
    out = []
    for p in sorted(root.rglob("*.sh")):
        if ".git" in p.parts:
            continue
        text = _read(p)
        if "set -e" not in text and "||" not in text and "&&" not in text:
            out.append(f"{p.relative_to(root).as_posix()}: no `set -e` and no per-step guard")
    return out


def q8_external_tools_only_stubbed(root):
    root = pathlib.Path(root)
    tools = set()
    for p in (root / "engine").rglob("*.py") if (root / "engine").is_dir() else []:
        tools.update(TOOL_CALL.findall(_read(p)))
    integ = "\n".join(_read(p) for p in (root / "integration").glob("*.py")) if (root / "integration").is_dir() else ""
    return [f"tool '{t}': invoked by the harness, exercised by no integration test" for t in sorted(tools) if t not in integ]


BORROWED_NAME = re.compile(r"(?i)(prod(uction)?|dump|export[-_]?\d{4}|backup|snapshot[-_]?\d{4}|real[-_]?data)")
BORROWED_READ = re.compile(r"""(?:open|read_text|read_bytes|Path)\(\s*["'](?:\.\./|/|[A-Za-z]:[\\/])""")
FIXTURE_SIZE_LIMIT = 64 * 1024


def q9_borrowed_fixtures(root):
    """Fixtures are constructed, not borrowed from production data (spec 05 REQ-2.4): a
    borrowed artifact stops exercising the case when production changes and nobody
    notices because it still parses. Reported: data files beside the tests that are
    large or named like a production capture, and test code that reads fixtures from
    outside the test tree."""
    root = pathlib.Path(root)
    out = []
    dirs = {p.parent for p in test_files(root)}
    for d in sorted(dirs):
        for p in sorted(x for x in d.rglob("*") if x.is_file()):
            if p.suffix == ".py" or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(root).as_posix()
            if p.stat().st_size > FIXTURE_SIZE_LIMIT:
                out.append(f"{rel}: {p.stat().st_size // 1024} KB data file beside the tests — a capture, not a constructed fixture")
            elif BORROWED_NAME.search(p.name):
                out.append(f"{rel}: named like a production capture")
    for p in test_files(root):
        for n, line in _code_lines(_read(p)):
            if BORROWED_READ.search(line):
                out.append(f"{p.relative_to(root).as_posix()}:{n}: reads a fixture from outside the test tree: {line.strip()[:90]}")
    return out


AUDIT_ID = "AUD-"


def finding_id(text):
    """A stable identifier for one audit finding, so its disposition can be recorded."""
    import hashlib
    where, _, rest = text.partition(": ")
    key = re.sub(r":\d+$", "", where) + "|" + rest[:60]
    return AUDIT_ID + hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


def dispositioned(root):
    """Audit finding ids that carry a row in the findings register (table A): the finding
    became a check or a checklist line (spec 05 REQ-10.2; spec 01 §1.4)."""
    from .records import findings as findings_mod
    try:
        a, _, _ = findings_mod.read(root)
    except OSError:
        return set()
    return {r["id"] for r in a if r["id"].startswith(AUDIT_ID)}


QUESTIONS = [
    ("1 dormant test files", q1_dormant_tests),
    ("2 checks without a negative fixture", None),   # needs the registry
    ("3 loops over discovered sets with no empty case", q3_loops_without_empty_guard),
    ("4 assertions on a class of values", q4_imprecise_assertions),
    ("5 assertions searching whole output", q5_whole_output_assertions),
    ("6 tests that skip on environment", q6_environment_dependent_tests),
    ("7 command sequences continuing past failure", q7_sequences_continuing_past_failure),
    ("8 external tools exercised only against stubs", q8_external_tools_only_stubbed),
    ("9 fixtures borrowed rather than constructed", q9_borrowed_fixtures),
]


def run(root, registry):
    """Return (lines, finding_count, could_not_run)."""
    root = pathlib.Path(root)
    lines = ["[audit] standing self-test audit (spec 05 §10)"]
    if not test_files(root):
        lines.append("[audit] COULD NOT RUN: no test files found — nothing to audit is not a clean audit")
        return lines, 0, True
    total = 0
    done = dispositioned(root)
    undispositioned = 0
    for title, fn in QUESTIONS:
        items = q2_checks_without_negative_fixture(root, registry) if fn is None else fn(root)
        lines.append(f"[audit] {title}: {len(items)} finding(s)")
        for i in items:
            fid = finding_id(i)
            tag = "dispositioned" if fid in done else "REQUIRES DISPOSITION"
            undispositioned += fid not in done
            lines.append(f"    - {fid} [{tag}] {i}")
        total += len(items)
    lines.append(f"[audit] {total} finding(s); {undispositioned} require disposition: each becomes a check or a checklist line, "
                 f"recorded in the findings register under its AUD- identifier")
    return lines, total, False
