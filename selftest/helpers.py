# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Shared fixture helpers. Every test constructs a throwaway tree and removes it
(spec 05 REQ-5.4); nothing here touches the network, a container runtime, or
the real repository."""
import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


@contextlib.contextmanager
def tree(prefix="engine-t-"):
    d = pathlib.Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def write(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def write_config(root, **over):
    data = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a",
            "mode": "local", "topology": "single", "side": "local", "operators": 1,
            "protected_branch": "main", "timezone": "UTC", "clock": "workstation clock",
            "not_applicable_threshold": 0.5}
    data.update(over)
    return write(root, ".engine/config.json", json.dumps(data, indent=2) + "\n")


def cli(root, *args):
    """Run the CLI in-process against a tree; return (exit, stdout lines)."""
    from engine.__main__ import main
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        code = main(["--root", str(root), *args])
    finally:
        sys.stdout = old
    return code, buf.getvalue().splitlines()


def cli_sub(root, *args):
    """Run the CLI as a real subprocess against a tree; return (exit, stdout lines).
    Use when the tree carries its own selftest/ package, which would collide with
    this one in-process."""
    res = subprocess.run([sys.executable, "-m", "engine", "--root", str(root), *args],
                         cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout.splitlines()


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def git_repo(root):
    """A throwaway git repository with a deterministic identity and no signing."""
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    return root


def commit(root, msg="c"):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg, "--allow-empty")
    return git(root, "rev-parse", "HEAD").stdout.strip()


def find_line(lines, prefix):
    """The one line starting with prefix, or raise naming what was observed."""
    hits = [l for l in lines if l.startswith(prefix)]
    if len(hits) != 1:
        raise AssertionError(f"expected exactly one line starting {prefix!r}, found {len(hits)}:\n" + "\n".join(lines))
    return hits[0]
