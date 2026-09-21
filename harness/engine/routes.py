# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Route inventory generated from the code (spec 01 REQ-5.2.4; spec 02 §9).

Routes are enumerated from the source, never from a hand-maintained list. The
inventory is the input to the negative-test set, so its accuracy is
load-bearing for a control. Recognised: Flask/FastAPI decorators, Django
paths, Express/Koa/Fastify handlers, NestJS decorators.
"""
import pathlib
import re

from . import gitutil
from .controlshape import TEST_PATH

PATTERNS = [
    ("py-decorator", re.compile(r"@[\w.]+\.(route|get|post|put|patch|delete|api_route)\(\s*((?:['\"][^'\"]*['\"]\s*,?\s*)+)")),
    ("django", re.compile(r"\b(?:path|re_path|url)\(\s*r?['\"]([^'\"]+)['\"]")),
    ("express", re.compile(r"\b(?:app|router|server|fastify)\.(get|post|put|patch|delete|all|use)\(\s*['\"`]([^'\"`]+)['\"`]")),
    ("nest", re.compile(r"@(Get|Post|Put|Patch|Delete)\(\s*['\"]([^'\"]*)['\"]?\s*\)")),
]
METHOD_FROM = {"route": "ANY", "api_route": "ANY", "use": "USE", "all": "ANY"}
VERBS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
RECORD_SCOPED = re.compile(r"<[^>]+>|:\w+|\{\w+\}|\(\?P<")
PRIVILEGE_OP = re.compile(r"(?i)(remove|delete|revoke|demote|deactivate|disable)_?(admin|owner|user|member|role|privilege)")
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def _files(root):
    root = pathlib.Path(root)
    files = gitutil.tracked_files(root) if gitutil.is_repo(root) else [
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [f for f in files if pathlib.Path(f).suffix in SOURCE_EXT and not TEST_PATH.search(f) and not f.startswith(".engine/")]


def inventory(root):
    """[{method, path, file, line, record_scoped}] generated from the tree."""
    root = pathlib.Path(root)
    out = []
    for rel in _files(root):
        p = root / rel
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for kind, pat in PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                if kind == "py-decorator":
                    # the path is the first string argument that looks like one; a router whose first
                    # argument is the verb (`route("GET", "/x")`) must not have "GET" taken as its path
                    args = re.findall(r"['\"]([^'\"]*)['\"]", m.group(2))
                    paths = [x for x in args if x.startswith("/")]
                    if not paths:
                        continue
                    path = paths[0]
                    verbs = [x.upper() for x in re.findall(r"['\"]([A-Za-z]+)['\"]", line) if x.upper() in VERBS]
                    method = verbs[0] if verbs else METHOD_FROM.get(m.group(1), m.group(1).upper())
                elif kind in ("express", "nest"):
                    method = m.group(1).upper()
                    method = METHOD_FROM.get(m.group(1), method)
                    path = m.group(2)
                else:
                    method, path = "ANY", m.group(1)
                out.append({"method": method, "path": path, "file": rel, "line": n,
                            "record_scoped": bool(RECORD_SCOPED.search(path))})
                break
    return out


def privileged_operations(root):
    """Functions whose name reads as removing a privileged principal."""
    root = pathlib.Path(root)
    out = []
    for rel in _files(root):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^\s*(?:async\s+)?(?:def|function)\s+(\w+)", text, re.M):
            if PRIVILEGE_OP.search(m.group(1)):
                out.append({"symbol": m.group(1), "file": rel, "line": text.count("\n", 0, m.start()) + 1})
    return out
