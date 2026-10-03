# © 2026 Casey Houle. All rights reserved.
"""Install the repository hooks into .git/hooks as thin shims."""
import pathlib
import stat
import subprocess

root = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip())
gitdir = pathlib.Path(subprocess.run(["git", "rev-parse", "--git-dir"], cwd=root,
                                     capture_output=True, text=True).stdout.strip())
if not gitdir.is_absolute():
    gitdir = root / gitdir
(gitdir / "hooks").mkdir(exist_ok=True)
# pre-commit is not installed: Casey Houle had it removed on 2026-10-02 (it ran the whole check on every
# commit); `check` stays green by the session's own runs and CI.
for name in ("commit-msg",):
    shim = gitdir / "hooks" / name
    # an app built on its own branch in a worktree of this repository has no work/hooks: nothing to run there
    shim.write_text('#!/bin/sh\nhook="$(git rev-parse --show-toplevel)/work/hooks/' + name + '.py"\n'
                    '[ -f "$hook" ] || exit 0\nexec python "$hook" "$@"\n', encoding="utf-8", newline="\n")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("installed", shim)
