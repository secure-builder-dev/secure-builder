# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Credential scan (spec 01 REQ-10.1, REQ-10.2, REQ-10.3).

Credential-shaped content in tracked files is a finding. One definition of a
credential serves both the routine check and the pre-commit hook, which scans
the staged index with `scan_staged` — never a parallel pattern set that drifts.
An inline allow annotation exists, and example/template files and obvious
placeholders are skipped, because a check with false positives is disabled
within a month.
"""
import pathlib
import re

from .. import gitutil
from ..outcome import Outcome

NAME = "credential-scan"
ALLOW = "engine:allow-credential"

PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abpr]-[0-9A-Za-z-]{10,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("assigned secret", re.compile(
        r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)"
        r"\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]")),
    ("connection string with password", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^:/\s]+:[^@/\s]{4,}@")),
    # spec 04 REQ-4.3.1: no registry credentials in any tracked file
    ("registry auth entry", re.compile(r"(?i)\"auth\"\s*:\s*\"[A-Za-z0-9+/=]{16,}\"")),
    ("registry login with password", re.compile(r"(?i)\b(docker|podman|nerdctl|crane|oras|helm\s+registry)\s+login\b.*(\s-p\s|--password[\s=](?!-stdin))")),
    ("registry token variable", re.compile(r"(?i)\b(docker|registry|ecr|acr|gcr|artifactory|nexus|harbor)[_-]?(token|password|passwd|auth)\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{12,}")),
]
PLACEHOLDER = re.compile(r"(?i)^(<[^>]+>|\$\{[^}]+\}|\{\{[^}]+\}\}|x{4,}|\*{4,}|changeme|change[-_]me|replace[-_]me|"
                         r"your[-_][a-z0-9_-]+|example|placeholder|dummy|todo|redacted|none|null|secret|password|"
                         r"[a-z_]*_here|test|testing|sample)$")
SKIP_NAME = re.compile(r"(?i)(\.example|\.template|\.sample|\.dist)$|(^|/)(examples?|templates?|samples?|fixtures?)/")
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar", ".jar", ".class", ".so", ".dll",
              ".exe", ".woff", ".woff2", ".ttf", ".pyc"}


def scan_text(path, text):
    """Findings in one file's text, as 'path:line: kind'."""
    out = []
    if SKIP_NAME.search(path):
        return out
    for n, line in enumerate(text.splitlines(), 1):
        if ALLOW in line:
            continue
        for kind, pat in PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            if kind == "assigned secret" and PLACEHOLDER.match(m.group(2).strip()):
                continue
            if kind == "assigned secret" and re.search(r"(?i)(os\.environ|getenv|process\.env|secrets?\.|vault)", line):
                continue
            out.append(f"{path}:{n}: {kind}")
            break
    return out


def _readable(p):
    return p.suffix.lower() not in BINARY_EXT and p.is_file() and p.stat().st_size < 2_000_000


def scan_tree(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    findings, scanned = [], 0
    for rel in files:
        p = root / rel
        if not _readable(p):
            continue
        scanned += 1
        findings += scan_text(rel, p.read_text(encoding="utf-8", errors="replace"))
    return scanned, findings


def scan_staged(root):
    """The same definition applied to the staged index (REQ-10.3)."""
    findings, scanned = [], 0
    for rel in gitutil.staged_files(root):
        if pathlib.Path(rel).suffix.lower() in BINARY_EXT:
            continue
        scanned += 1
        findings += scan_text(rel, gitutil.staged_text(root, rel))
    return scanned, findings


def run(root, cfg):
    scanned, findings = scan_tree(root)
    if scanned == 0:
        return Outcome.could_not_run(NAME, "no readable tracked files to scan")
    if findings:
        return Outcome.found(NAME, f"credential-shaped content in {len(findings)} place(s) across {scanned} files",
                             findings, blocking=True)
    return Outcome.clean(NAME, f"{scanned} tracked files carry no credential-shaped content")
