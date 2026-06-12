#!/usr/bin/env python3
"""secret_scan.py — Pre-commit secret & forbidden-file scan (Guarantee #7, §11).

Blocks a commit that would stage:
  (a) a FORBIDDEN FILE — helm values files, *.tfvars, POA&M / scan-result files
      (CLAUDE.md §8 / PRD §11), or
  (b) a probable SENSITIVE VALUE — AWS account id, ARN, private key block, etc.

This is a backstop, NOT the primary control. The primary control for Guarantee #7 is
STRUCTURAL SEPARATION — keeping sensitive values outside the repo the agent can see
(CLAUDE.md §8). A pattern scan catches accidents; it does not make it safe to put real
infra values in the workspace. Expect false positives; tune patterns per project.

Stdlib only.

Usage:
    secret_scan.py --staged          # scan staged (index) content — pre-commit use
    secret_scan.py --files a b c     # scan specific files

Exit codes: 0 = clean, 1 = finding(s), 2 = usage error.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_PATHS = [
    re.compile(r"(^|/)helm/values-(dev|prod|staging)\.ya?ml$"),
    re.compile(r"\.tfvars$"),
    re.compile(r"(^|/)(poa&?m|poam)[^/]*$", re.I),
    re.compile(r"(^|/)anchore[^/]*\.(json|txt|xml)$", re.I),
]

# Probable sensitive VALUES. Deliberately conservative to limit false positives.
VALUE_PATTERNS = [
    ("AWS account id (12 digits in arn/acct context)", re.compile(r"(?:account[_-]?id|:)\D?(\d{12})\b", re.I)),
    ("AWS ARN", re.compile(r"\barn:aws[a-z\-]*:[a-z0-9\-]*:[a-z0-9\-]*:\d{12}:")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("Security group id", re.compile(r"\bsg-[0-9a-f]{8,17}\b")),
    ("Generic secret assignment", re.compile(r"(?i)\b(secret|password|passwd|client_secret|api[_-]?key)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]

PLACEHOLDER = re.compile(r"<[A-Z_]+>|EXAMPLE|REDACTED|XXXX|\bplaceholder\b", re.I)


def staged_files():
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"error: git failed: {out.stderr.strip()}")
    return [l.replace("\\", "/") for l in out.stdout.splitlines() if l.strip()]


def staged_content(path):
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f":{path}"],
        capture_output=True, text=True,
    )
    return out.stdout if out.returncode == 0 else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--files", nargs="+")
    a = ap.parse_args()

    files = staged_files() if a.staged else [f.replace("\\", "/") for f in a.files]
    findings = []

    for path in files:
        for rx in FORBIDDEN_PATHS:
            if rx.search(path):
                findings.append((path, 0, "FORBIDDEN FILE — must never be tracked (PRD §11)"))
        content = staged_content(path) if a.staged else _read(path)
        for i, line in enumerate(content.splitlines(), 1):
            if PLACEHOLDER.search(line):
                continue
            for label, rx in VALUE_PATTERNS:
                if rx.search(line):
                    findings.append((path, i, f"probable {label}"))

    if not findings:
        print(f"secret_scan: clean ({len(files)} file(s) scanned).")
        return 0
    print(f"secret_scan: {len(findings)} FINDING(S) — commit blocked:")
    for path, line, why in findings:
        loc = f"{path}:{line}" if line else path
        print(f"  - {loc} — {why}")
    print("  → Remove the value/file. Use placeholders (<ACCOUNT_ID>, <CERT_ARN>).")
    print("    Primary control is structural separation, not this scan (CLAUDE.md §8).")
    return 1


def _read(path):
    try:
        return Path(REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
