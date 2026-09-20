# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""External tool invocation.

Every external tool the harness runs (a container runtime, a scanner binary,
version control) goes through here. Tools are resolved on the search path with
PATHEXT honoured, so a self-test can stub one by placing an executable earlier
on the path (spec 05 REQ-5.2), and the stub can record what was called
(REQ-5.3). A tool that cannot be resolved is reported as such — never treated
as a clean run.

Exit codes are returned exactly. Callers assert the specific value that means
success or detection; every other value is "the tool fell over" (REQ-4.2).
"""
import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class Result:
    tool: str
    args: list
    exit_code: int
    stdout: str
    stderr: str
    resolved: str

    @property
    def ran(self):
        return self.resolved != ""


def resolve(name, path=None):
    """Absolute path of the tool, or '' when it is not on the search path."""
    found = shutil.which(name, path=path if path is not None else os.environ.get("PATH", ""))
    return found or ""


def run_tool(name, args, *, cwd=None, path=None, timeout=600, env=None):
    exe = resolve(name, path)
    if not exe:
        return Result(name, list(args), -1, "", f"{name}: not found on the search path", "")
    run_env = dict(os.environ)
    if path is not None:
        run_env["PATH"] = path
    if env:
        run_env.update(env)
    try:
        res = subprocess.run([exe, *args], cwd=cwd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=timeout, env=run_env)
    except subprocess.TimeoutExpired:
        return Result(name, list(args), -2, "", f"{name}: timed out after {timeout}s", exe)
    return Result(name, list(args), res.returncode, res.stdout, res.stderr, exe)
