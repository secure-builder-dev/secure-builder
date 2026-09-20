# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The failure semantics — the honesty rules (spec 01 §1.2, §13; spec 11 §5).

Every check in the harness returns an Outcome. There are six states and they
are never reported with the same wording:

  CLEAN           checked, clean — ran against real input, found nothing.   exit 0
  FINDINGS        checked, findings.                                        exit 1
  COULD_NOT_RUN   the check was prevented from running.                     exit 2
  NOT_APPLICABLE  nothing to run against, structurally, on this shape.      exit 0
                  MUST name the shape and what covers that ground instead.
  NOTHING_YET     the project has not grown the surface but may.            exit 0
  DEFERRED        applies, could have run, was not run — and is owed.       exit 3
                  (field mode, spec 11). Never reported as skipped or NA.

A zero exit means "ran against real input and found nothing" or a structural
non-applicability that says so in words. Nothing else exits zero.
"""
from dataclasses import dataclass, field
from enum import Enum


class State(Enum):
    CLEAN = "checked-clean"
    FINDINGS = "checked-findings"
    COULD_NOT_RUN = "could-not-run"
    NOT_APPLICABLE = "not-applicable"
    NOTHING_YET = "nothing-to-check-yet"
    DEFERRED = "deferred"


EXIT = {
    State.CLEAN: 0,
    State.NOT_APPLICABLE: 0,
    State.NOTHING_YET: 0,
    State.FINDINGS: 1,
    State.COULD_NOT_RUN: 2,
    State.DEFERRED: 3,
}

WORDING = {
    State.CLEAN: "CLEAN",
    State.FINDINGS: "FINDINGS",
    State.COULD_NOT_RUN: "COULD NOT RUN",
    State.NOT_APPLICABLE: "NOT APPLICABLE",
    State.NOTHING_YET: "NOTHING TO CHECK YET",
    State.DEFERRED: "DEFERRED",
}


@dataclass
class Outcome:
    check: str
    state: State
    detail: str = ""
    findings: list = field(default_factory=list)
    blocking: bool = False
    shape: str = ""      # NOT_APPLICABLE / NOTHING_YET: the project shape that makes it so
    covers: str = ""     # NOT_APPLICABLE: what covers that ground instead — or "nothing"
    reason: str = ""     # DEFERRED: why (e.g. "budget")

    def __post_init__(self):
        if self.state is State.NOT_APPLICABLE:
            if not self.shape.strip():
                raise ValueError(f"{self.check}: NOT_APPLICABLE must name the project shape")
            if not self.covers.strip():
                raise ValueError(f"{self.check}: NOT_APPLICABLE must state what covers that ground "
                                 "(or the word 'nothing')")
        if self.state is State.NOTHING_YET and not self.shape.strip():
            raise ValueError(f"{self.check}: NOTHING_YET must name the surface not yet grown")
        if self.state is State.DEFERRED and not self.reason.strip():
            raise ValueError(f"{self.check}: DEFERRED must carry a reason")
        if self.state is State.FINDINGS and not self.findings:
            raise ValueError(f"{self.check}: FINDINGS with an empty findings list is not a finding")
        if self.state is not State.FINDINGS and self.blocking:
            raise ValueError(f"{self.check}: only FINDINGS may block")

    @property
    def exit_code(self):
        return EXIT[self.state]

    @property
    def applicable(self):
        return self.state in (State.CLEAN, State.FINDINGS, State.COULD_NOT_RUN, State.DEFERRED)

    @property
    def failed(self):
        return self.state in (State.FINDINGS, State.COULD_NOT_RUN, State.DEFERRED)

    def line(self):
        """The single line that carries the claim. Assertions target this line."""
        w = WORDING[self.state]
        if self.state is State.NOT_APPLICABLE:
            return f"[{self.check}] {w} on shape '{self.shape}': {self.detail} — covered instead by: {self.covers}"
        if self.state is State.NOTHING_YET:
            return f"[{self.check}] {w}: project has no {self.shape} yet — {self.detail}"
        if self.state is State.DEFERRED:
            return f"[{self.check}] {w} (reason: {self.reason}) — owed; {self.detail}"
        if self.state is State.FINDINGS:
            tag = " BLOCKING" if self.blocking else ""
            return f"[{self.check}] {w}{tag}: {len(self.findings)} finding(s) — {self.detail}"
        return f"[{self.check}] {w}: {self.detail}"

    def lines(self):
        out = [self.line()]
        out += [f"    - {f}" for f in self.findings]
        return out

    # constructors that make the required fields impossible to forget
    @classmethod
    def clean(cls, check, detail):
        return cls(check, State.CLEAN, detail)

    @classmethod
    def found(cls, check, detail, items, blocking=False):
        return cls(check, State.FINDINGS, detail, findings=list(items), blocking=blocking)

    @classmethod
    def could_not_run(cls, check, detail):
        return cls(check, State.COULD_NOT_RUN, detail)

    @classmethod
    def not_applicable(cls, check, shape, detail, covers):
        return cls(check, State.NOT_APPLICABLE, detail, shape=shape, covers=covers)

    @classmethod
    def nothing_yet(cls, check, surface, detail):
        return cls(check, State.NOTHING_YET, detail, shape=surface)

    @classmethod
    def deferred(cls, check, reason, detail):
        return cls(check, State.DEFERRED, detail, reason=reason)


@dataclass
class Summary:
    """Aggregate counts, reported separately (spec 01 REQ-13.2.3)."""
    outcomes: list
    na_threshold: float = 0.5

    def count(self, *states):
        return sum(1 for o in self.outcomes if o.state in states)

    @property
    def applicable(self):
        return sum(1 for o in self.outcomes if o.applicable)

    @property
    def not_applicable(self):
        return self.count(State.NOT_APPLICABLE)

    @property
    def nothing_yet(self):
        return self.count(State.NOTHING_YET)

    @property
    def failed(self):
        return sum(1 for o in self.outcomes if o.failed)

    @property
    def deferred(self):
        return self.count(State.DEFERRED)

    @property
    def na_proportion(self):
        n = len(self.outcomes)
        return (self.not_applicable / n) if n else 0.0

    @property
    def na_over_threshold(self):
        return len(self.outcomes) > 0 and self.na_proportion > self.na_threshold

    def line(self):
        if not self.outcomes:
            return "[summary] COULD NOT RUN: zero checks were discovered — an empty suite is not a pass"
        s = (f"[summary] {len(self.outcomes)} checks: {self.applicable} applicable, "
             f"{self.not_applicable} not applicable, {self.nothing_yet} nothing-yet, "
             f"{self.deferred} deferred, {self.failed} failed")
        return s

    def disposition_lines(self):
        out = []
        if self.na_over_threshold:
            unguarded = [o for o in self.outcomes if o.state is State.NOT_APPLICABLE]
            out.append(f"[summary] FINDING (non-blocking, requires disposition): "
                       f"{self.not_applicable}/{len(self.outcomes)} checks not applicable "
                       f"({self.na_proportion:.0%} > {self.na_threshold:.0%}). "
                       f"This project shape is covered by {self.applicable} check(s); unguarded ground:")
            for o in unguarded:
                out.append(f"    - {o.check}: {o.detail}; covered instead by: {o.covers}")
        return out

    @property
    def exit_code(self):
        if not self.outcomes:
            return 2
        return max(o.exit_code for o in self.outcomes)
