# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Injection scan (spec 01 REQ-10.1; §13.2 worked example).

String-built queries in application source are findings. The scanner reads the
web track's languages (JavaScript/TypeScript and Python). On a track whose
language it does not read, it says NOT APPLICABLE, names the track, says what
it reads, and states that persistence in the project's actual language is
covered by no check — which is the only honest form of not-applicable.
"""
import pathlib
import re

from .. import gitutil
from ..outcome import Outcome

NAME = "injection-scan"
READS = {"web": (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py")}
SQL = r"(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from|drop\s+table|where\s)"
PATTERNS = [
    ("concatenated SQL", re.compile(r"(?i)(query|execute|executemany|raw|exec)\s*\(\s*(?:f?['\"`]" + SQL + r".*?['\"`]\s*\+|['\"`][^'\"`]*['\"`]\s*\+\s*\w+.*?" + SQL + ")")),
    ("f-string SQL", re.compile(r"(?i)(query|execute|executemany|raw|exec)\s*\(\s*f['\"]" + SQL + r"[^'\"]*\{")),
    ("template-literal SQL", re.compile(r"(?i)(query|execute|raw|exec)\s*\(\s*`[^`]*" + SQL + r"[^`]*\$\{")),
    ("format SQL", re.compile(r"(?i)(query|execute|executemany|raw|exec)\s*\(\s*['\"]" + SQL + r"[^'\"]*['\"]\s*(\.format\(|%\s*[\w(])")),
]
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__|selftest|fixtures?)/|[._-]test\.|_test\.py$|\.spec\.")


def scan_text(path, text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if "engine:allow-injection" in line:
            continue
        for kind, pat in PATTERNS:
            if pat.search(line):
                out.append(f"{path}:{n}: {kind}")
                break
    return out


def run(root, cfg):
    track = cfg.track if cfg else "unset"
    exts = READS.get(track)
    if exts is None:
        return Outcome.not_applicable(
            NAME, f"track={track}",
            "this scanner reads JavaScript/TypeScript and Python source for string-built queries",
            "nothing — persistence code in this track's language is checked by no injection scan")
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    source = [f for f in files if pathlib.Path(f).suffix in exts and not TEST_PATH.search(f)
              and not f.startswith(".engine/")]
    if not source:
        return Outcome.nothing_yet(NAME, "application source in a language this scanner reads",
                                   "no non-test JavaScript/TypeScript/Python files are tracked")
    findings = []
    for rel in source:
        p = root / rel
        if p.is_file():
            findings += scan_text(rel, p.read_text(encoding="utf-8", errors="replace"))
    if findings:
        return Outcome.found(NAME, f"string-built queries in {len(findings)} place(s)", findings, blocking=True)
    return Outcome.clean(NAME, f"{len(source)} application source files build no queries from strings")
