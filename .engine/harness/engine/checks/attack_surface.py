# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Attack-surface diff (spec 01 REQ-10.1).

A previously-absent risky directive appearing in server or deployment
configuration is a finding. The set of accepted directives lives in a
project-owned, committed baseline; a directive present in the tree and not in
the baseline blocks until a person accepts it into the baseline with a reason.
No configuration surface at all is "nothing to check yet", not a pass.
"""
import json
import pathlib
import re

from .. import gitutil
from ..outcome import Outcome

NAME = "attack-surface"
BASELINE = ".engine/records/attack-surface-baseline.json"
CONFIG_FILES = re.compile(r"(?i)(^|/)(nginx[^/]*\.conf|httpd\.conf|apache2?\.conf|\.htaccess|Dockerfile[^/]*|docker-compose[^/]*\.ya?ml|"
                          r"compose\.ya?ml|[^/]*\.ya?ml|[^/]*\.tf|web\.config|Caddyfile|[^/]*\.env|settings\.py|config\.(js|ts|json))$")
DIRECTIVES = [
    ("directory listing", re.compile(r"(?i)^\s*autoindex\s+on|Options\s+[^#\n]*\+?Indexes")),
    ("permissive override", re.compile(r"(?i)^\s*AllowOverride\s+All")),
    ("wildcard CORS", re.compile(r"(?i)(Access-Control-Allow-Origin[\"']?\s*[:=,]\s*[\"']?\*|cors\s*\(\s*\)|origin\s*[:=]\s*[\"']\*[\"'])")),
    ("debug enabled", re.compile(r"(?i)^\s*(DEBUG|FLASK_DEBUG|APP_DEBUG|NODE_ENV)\s*[:=]\s*[\"']?(true|1|development)[\"']?\s*$")),
    ("TLS verification off", re.compile(r"(?i)(ssl_verify(_client)?\s*[:=]?\s*(false|off)|verify\s*=\s*False|insecure[-_]skip[-_]verify\s*[:=]\s*true|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*0)")),
    ("privileged container", re.compile(r"(?i)(privileged\s*[:=]\s*true|--privileged\b)")),
    ("host network", re.compile(r"(?i)(hostNetwork\s*:\s*true|network_mode\s*:\s*[\"']?host)")),
    ("privilege escalation", re.compile(r"(?i)allowPrivilegeEscalation\s*:\s*true")),
    ("root user", re.compile(r"(?i)(runAsUser\s*:\s*0\b|^\s*USER\s+root\s*$)")),
    ("docker socket mount", re.compile(r"/var/run/docker\.sock")),
    ("bind all interfaces with management port", re.compile(r"(?i)0\.0\.0\.0:(22|2375|2376|3306|5432|6379|27017|9200|15672)\b")),
    ("plaintext protocol", re.compile(r"(?i)(^\s*listen\s+80\s*;|proxy_pass\s+http://|ftp://|telnet://)")),
    ("weak TLS", re.compile(r"(?i)ssl_protocols[^;\n]*(SSLv2|SSLv3|TLSv1(\.0|\.1)?\b(?!\.[23]))")),
]


def config_files(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [f for f in files if CONFIG_FILES.search(f) and not f.startswith((".engine/", ".github/"))]


def directives_in(root):
    """{'path:kind': line} for every risky directive found."""
    root = pathlib.Path(root)
    found = {}
    for rel in config_files(root):
        p = root / rel
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "engine:allow-directive" in line:
                continue
            for kind, pat in DIRECTIVES:
                if pat.search(line):
                    found[f"{rel}:{kind}"] = f"{rel}:{n}: {line.strip()[:80]}"
                    break
    return found


def read_baseline(root):
    p = pathlib.Path(root) / BASELINE
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data.get("accepted", {}) if isinstance(data, dict) else None


def accept(root, key, reason, by):
    """Accept a directive into the baseline — a human decision, recorded with its reason."""
    p = pathlib.Path(root) / BASELINE
    data = {"accepted": {}}
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("accepted", {})[key] = {"reason": reason, "by": by}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(root, cfg):
    files = config_files(root)
    if not files:
        return Outcome.nothing_yet(NAME, "server or deployment configuration", "no configuration files are tracked")
    baseline = read_baseline(root)
    if baseline is None:
        return Outcome.could_not_run(NAME, f"{BASELINE} is unreadable")
    found = directives_in(root)
    new = [f"{v} [{k.split(':', 1)[1]}] — accept with `engine accept-directive` and a reason"
           for k, v in sorted(found.items()) if k not in baseline]
    stale = [k for k in baseline if k not in found]
    if new:
        return Outcome.found(NAME, f"{len(new)} risky directive(s) not in the accepted baseline across {len(files)} config files",
                             new, blocking=True)
    detail = f"{len(files)} config files; {len(found)} risky directive(s), all previously accepted"
    if stale:
        detail += f"; {len(stale)} baseline entr(y/ies) no longer present"
    return Outcome.clean(NAME, detail)
