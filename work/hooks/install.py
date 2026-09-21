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
for name in ("pre-commit", "commit-msg"):
    shim = gitdir / "hooks" / name
    shim.write_text('#!/bin/sh\nexec python "$(git rev-parse --show-toplevel)/work/hooks/' + name + '.py" "$@"\n',
                    encoding="utf-8", newline="\n")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("installed", shim)
