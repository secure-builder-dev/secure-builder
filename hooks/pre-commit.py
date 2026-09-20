# © 2026 Casey Houle. All rights reserved.
"""pre-commit — enforcement outside the assistant's judgment (spec 07 §6).

Refuses the commit when:
  1. a staged file is in the build's governance set and ENGINE_GOVERNANCE_OK=1
     is not in the environment (an explicit human approval per commit);
  2. any ledger row claims `done` without an existing impl and a valid receipt
     (tools/progress.py --drift-only);
  3. `python -m engine check` is red — once the engine package exists. Until it
     exists this prints "check: not configured" and does not pretend to pass;
  4. a staged authored file (.py .md .sh .txt .toml .json under the repo, not
     under specs/ receipts/ .journal/ or ledger.tsv) lacks the copyright header;
  5. a staged file outside specs/ mentions an AI assistant or carries an
     attribution trailer — only Casey Houle's name lands in this repository.

Every refusal names the file and the rule. A hook that blocks broadly gets
disabled (spec 03 REQ-4.3), so this blocks exactly these five things.
"""
import datetime
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())
GOVERNANCE = ("v1.0.md", "tools/progress.py", "tools/progress_test.py", "hooks/",
              "prompts/iteration.md", "specs/", "GOVERNANCE-SET.md", "AMENDMENTS.md")
HEADER = "© 2026 Casey Houle. All rights reserved."
HEADER_EXT = (".py", ".md", ".sh", ".txt", ".toml", ".json", ".yaml", ".yml", ".cfg")
HEADER_EXEMPT = ("specs/", "receipts/", ".journal/", ".engine/", "ledger.tsv", ".gitattributes",
                 ".gitignore", "LICENSE", "budget.txt")
FORBIDDEN = re.compile(r"co-authored-by|\bclaude\b|\banthropic\b|\bopenai\b|\bcopilot\b|generated with \[", re.I)


def staged():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                         capture_output=True, text=True).stdout
    return [p for p in out.splitlines() if p.strip()]


def staged_text(path):
    res = subprocess.run(["git", "show", f":{path}"], capture_output=True)
    return res.stdout.decode("utf-8", errors="replace")


def main():
    files = staged()
    refusals = []

    gov = [f for f in files if any(f == g or f.startswith(g) for g in GOVERNANCE)]
    if gov and os.environ.get("ENGINE_GOVERNANCE_OK") != "1":
        refusals.append("governance set touched without ENGINE_GOVERNANCE_OK=1: " + ", ".join(gov))

    for f in files:
        if f.startswith("specs/"):
            continue
        text = staged_text(f)
        exempt = any(f == e or f.startswith(e) for e in HEADER_EXEMPT)
        if not exempt and f.endswith(HEADER_EXT) and HEADER not in text:
            refusals.append(f"missing copyright header: {f}")
        m = None if f.startswith("hooks/") else FORBIDDEN.search(text)
        if m:
            refusals.append(f"assistant attribution or name in {f}: {m.group(0)!r}")

    if (ROOT / "ledger.tsv").is_file():
        res = subprocess.run([sys.executable, str(ROOT / "tools/progress.py"), "--drift-only"],
                             capture_output=True, text=True, cwd=str(ROOT))
        if res.returncode != 0:
            refusals.append("ledger claims done falsely:\n    " + res.stdout.strip().replace("\n", "\n    "))

    if (ROOT / "engine" / "__main__.py").is_file():
        res = subprocess.run([sys.executable, "-m", "engine", "check"], capture_output=True,
                             text=True, cwd=str(ROOT))
        if res.returncode != 0:
            tail = "\n    ".join((res.stdout + res.stderr).strip().splitlines()[-5:])
            refusals.append(f"`python -m engine check` is red (exit {res.returncode}):\n    {tail}")
        else:
            print("pre-commit: check green")
    else:
        print("pre-commit: check not configured (no engine package yet)")

    if refusals:
        print("pre-commit: REFUSED")
        for r in refusals:
            print("  - " + r)
        return 1
    if gov:
        (ROOT / ".journal").mkdir(exist_ok=True)
        with (ROOT / ".journal" / "governance").open("a", encoding="utf-8") as j:
            stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
            j.write(f"{stamp} governance files staged with human approval: {', '.join(gov)}\n")
    print(f"pre-commit: ok ({len(files)} staged file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
