# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Lint and type checking, track-appropriate (spec 01 REQ-10.1).

The command comes from the configuration (`lint_command`, optionally
`typecheck_command`), or from the project's own manifest for the track. A
project that has configured nothing is "nothing to check yet"; a configured
tool that cannot be found or run is "could not run" — never a pass.
"""
import json
import pathlib

from .. import tools
from ..outcome import Outcome

NAME = "lint"


def commands_for(root, cfg):
    root = pathlib.Path(root)
    cmds = []
    if cfg and cfg.get("lint_command"):
        cmds.append(("lint", list(cfg.get("lint_command"))))
    if cfg and cfg.get("typecheck_command"):
        cmds.append(("typecheck", list(cfg.get("typecheck_command"))))
    if cmds:
        return cmds
    track = cfg.track if cfg else "unset"
    if track == "web" and (root / "package.json").is_file():
        try:
            scripts = json.loads((root / "package.json").read_text(encoding="utf-8")).get("scripts", {})
        except ValueError:
            scripts = {}
        if "lint" in scripts:
            cmds.append(("lint", ["npm", "run", "lint", "--silent"]))
        if "typecheck" in scripts:
            cmds.append(("typecheck", ["npm", "run", "typecheck", "--silent"]))
    elif track == "android" and (root / "gradlew").is_file():
        cmds.append(("lint", ["./gradlew", "lint", "-q"]))
    return cmds


def run(root, cfg):
    cmds = commands_for(root, cfg)
    if not cmds:
        return Outcome.nothing_yet(NAME, "lint or type-check configuration",
                                   "no lint_command/typecheck_command is configured and the track's manifest declares none")
    findings, ran = [], []
    for kind, cmd in cmds:
        res = tools.run_tool(cmd[0], cmd[1:], cwd=str(root))
        if not res.ran:
            return Outcome.could_not_run(NAME, f"{kind} tool '{cmd[0]}' is not on the search path")
        if res.exit_code < 0:
            return Outcome.could_not_run(NAME, f"{kind}: {res.stderr.strip()}")
        ran.append(f"{kind} ({' '.join(cmd)}) exit {res.exit_code}")
        if res.exit_code != 0:
            tail = (res.stdout + res.stderr).strip().splitlines()[-5:]
            findings.append(f"{kind} failed (exit {res.exit_code}): " + " | ".join(tail))
    if findings:
        return Outcome.found(NAME, "; ".join(ran), findings, blocking=True)
    return Outcome.clean(NAME, "; ".join(ran))
