# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Verification before irreversible action (spec 05 §8)."""
import unittest

from engine import sequence
from engine.sequence import Step


class StopsAtFailure(unittest.TestCase):
    def test_nothing_after_a_failed_step_runs(self):
        ran = []
        steps = [Step("verify", lambda: (ran.append("verify"), False)[1]),
                 Step("commit", lambda: ran.append("commit"), irreversible=True)]
        r = sequence.run(steps)
        self.assertFalse(r.ok)
        self.assertEqual(r.stopped_at, "verify")
        self.assertEqual(ran, ["verify"], "the irreversible step must not run after a failed verification")
        self.assertEqual(r.line(), "[sequence] STOPPED at 'verify' after 0 step(s); nothing after it ran — step returned False")

    def test_nonzero_int_is_failure(self):
        r = sequence.run([Step("check", lambda: 1), Step("push", lambda: 0)])
        self.assertEqual((r.stopped_at, r.completed), ("check", []))

    def test_exception_is_failure_not_continuation(self):
        def boom():
            raise RuntimeError("no")
        r = sequence.run([Step("a", lambda: 0), Step("b", boom), Step("c", lambda: 0)])
        self.assertEqual(r.completed, ["a"])
        self.assertEqual(r.stopped_at, "b")
        self.assertEqual(r.error, "RuntimeError: no")

    def test_all_pass(self):
        r = sequence.run([Step("a", lambda: None), Step("b", lambda: True), Step("c", lambda: 0)])
        self.assertTrue(r.ok)
        self.assertEqual(r.line(), "[sequence] completed 3 step(s): a, b, c")

    def test_object_with_ok_attribute(self):
        class R:
            ok = False
        r = sequence.run([Step("a", lambda: R())])
        self.assertEqual(r.stopped_at, "a")
