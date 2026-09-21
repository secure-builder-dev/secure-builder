# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Where the harness's own tree is, from a project root.

Four folders hold everything the engine owns or produces, in both places it lives:
rules/ (what the system promised), harness/ (what checks it), records/ (what it
found), work/ (scratch). In the build repository they sit at the root; in a project
they sit under .engine/. The harness tree itself — the package, the self-tests, the
reviewer drivers, run.py — has the same shape in both: `harness/engine`,
`harness/selftest`, `harness/reviewers`, `harness/run.py`.
"""
import pathlib


def harness_dir(root):
    """The directory holding engine/ and selftest/, or None. The build repository's `harness/`,
    a project's `.engine/harness/`, or the root itself (a fixture tree with engine/ at its top)."""
    root = pathlib.Path(root)
    for cand in (root / "harness", root / ".engine" / "harness", root):
        if (cand / "engine" / "checks" / "__init__.py").is_file():
            return cand
    return None


def package_dir(root):
    h = harness_dir(root)
    return h / "engine" if h else None


def rel(root, path):
    """A path relative to root, posix, or the path itself when outside."""
    try:
        return pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve()).as_posix()
    except ValueError:
        return pathlib.Path(path).as_posix()
