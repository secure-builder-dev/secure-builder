# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Verification before irreversible action (spec 05 §8; spec 01 REQ-13.5.1).

A sequence of steps stops at the first step that fails. Nothing after a failed
verification runs, by default, without each caller having to remember a guard.
The record of the sequence names the step that stopped it, so a log never shows
diligence that did not occur.
"""
from dataclasses import dataclass, field


@dataclass
class Step:
    name: str
    fn: object                     # callable returning True/0/None for success
    irreversible: bool = False


@dataclass
class Run:
    completed: list = field(default_factory=list)
    stopped_at: str = ""
    error: str = ""

    @property
    def ok(self):
        return not self.stopped_at

    def line(self):
        if self.ok:
            return f"[sequence] completed {len(self.completed)} step(s): {', '.join(self.completed)}"
        return (f"[sequence] STOPPED at '{self.stopped_at}' after {len(self.completed)} step(s); "
                f"nothing after it ran — {self.error}")


def _succeeded(value):
    if value is None or value is True:
        return True
    if value is False:
        return False
    if isinstance(value, int):
        return value == 0
    return bool(getattr(value, "ok", False))


def run(steps):
    r = Run()
    for step in steps:
        try:
            value = step.fn()
        except Exception as e:  # a raising step is a failed step
            r.stopped_at = step.name
            r.error = f"{type(e).__name__}: {e}"
            return r
        if not _succeeded(value):
            r.stopped_at = step.name
            r.error = f"step returned {value!r}"
            return r
        r.completed.append(step.name)
    return r
