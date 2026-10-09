# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Executable stubs for external tools (spec 05 §5).

A stub is placed in a directory that is put first on the search path. It exits
with the code the test chose, prints what the test chose, and appends every
invocation (name and arguments) to an invocations log, so a test can assert
what was called and not only what was printed.
"""
import os
import pathlib
import stat
import sys

LOG = "invocations.log"


def stub_tool(directory, name, exit_code=0, stdout="", stderr=""):
    """Create a stub named `name` in `directory` for the current platform."""
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / LOG
    body = (
        "import sys, pathlib\n"
        f"pathlib.Path({str(log)!r}).open('a', encoding='utf-8').write({name!r} + ' ' + ' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({int(exit_code)})\n"
    )
    script = directory / f"{name}.stub.py"
    script.write_text(body, encoding="utf-8", newline="\n")
    if os.name == "nt":
        wrapper = directory / f"{name}.bat"
        wrapper.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8", newline="")
    else:
        wrapper = directory / name
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8", newline="\n")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return wrapper


def stub_path(directory):
    """A PATH value with `directory` first, so stubs shadow real tools."""
    return str(directory) + os.pathsep + os.environ.get("PATH", "")


def invocations(directory):
    log = pathlib.Path(directory) / LOG
    if not log.is_file():
        return []
    return log.read_text(encoding="utf-8").splitlines()
