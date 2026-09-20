# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The entrypoint a project invokes: `python .engine/harness/run.py <command>`.
Runs the placed copy of the harness against the project root."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine.__main__ import main  # noqa: E402

if __name__ == "__main__":
    root = HERE.parent.parent
    sys.exit(main(["--root", str(root), *sys.argv[1:]]))
