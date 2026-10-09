# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The entrypoint: `python .engine/harness/run.py <command>` in a project, `python harness/run.py
<command>` in the harness repository itself. The tree under harness/ has the same shape in both
places; the root is the directory that holds .engine/, or the repository when harness/ sits at its top."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine.__main__ import main  # noqa: E402

if __name__ == "__main__":
    root = HERE.parent.parent if HERE.parent.name == ".engine" else HERE.parent
    sys.exit(main(["--root", str(root), *sys.argv[1:]]))
