# © 2026 Casey Houle. All rights reserved.
"""commit-msg — refuses any commit message carrying an attribution trailer or an
AI assistant's name. The author and signer of every commit is Casey Houle."""
import pathlib
import re
import sys

FORBIDDEN = re.compile(r"co-authored-by|\bclaude\b|\banthropic\b|\bopenai\b|\bcopilot\b|generated with", re.I)

text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
body = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
m = FORBIDDEN.search(body)
if m:
    print(f"commit-msg: REFUSED — message contains {m.group(0)!r}; only Casey Houle is attributed")
    sys.exit(1)
sys.exit(0)
