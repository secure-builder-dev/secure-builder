# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Version-control access. Every question about the tree's history is asked of
git directly, never of a file some earlier session wrote (spec 03 REQ-3.4.2).
Reads come straight from the repository (spec 01 REQ-6.1.3): a diff is never
accepted as input."""
import subprocess


def git(root, *args, check=False):
    res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {res.stderr.strip()}")
    return res


def is_repo(root):
    return git(root, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true"


def head(root):
    res = git(root, "rev-parse", "HEAD")
    return res.stdout.strip() if res.returncode == 0 else ""


def rev(root, name):
    res = git(root, "rev-parse", "--verify", "--quiet", name)
    return res.stdout.strip() if res.returncode == 0 else ""


def current_branch(root):
    return git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def protected_ref(root, branch):
    """The protected branch as seen from the remote first (spec 03 REQ-3.4.3), else locally."""
    for name in (f"origin/{branch}", branch):
        if rev(root, name):
            return name
    return ""


def merge_base(root, a, b):
    res = git(root, "merge-base", a, b)
    return res.stdout.strip() if res.returncode == 0 else ""


def changed_files(root, base, head_):
    res = git(root, "diff", "--name-only", f"{base}..{head_}")
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []


def commits_in(root, base, head_):
    res = git(root, "rev-list", f"{base}..{head_}")
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []


def tracked_files(root):
    res = git(root, "ls-files")
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []


def staged_files(root):
    res = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []


def staged_text(root, path):
    res = subprocess.run(["git", "-C", str(root), "show", f":{path}"], capture_output=True)
    return res.stdout.decode("utf-8", errors="replace") if res.returncode == 0 else ""


def diff_text(root, base, head_):
    res = git(root, "diff", f"{base}..{head_}")
    return res.stdout if res.returncode == 0 else ""


def log_subjects(root, base, head_):
    res = git(root, "log", "--format=%s", f"{base}..{head_}")
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []
