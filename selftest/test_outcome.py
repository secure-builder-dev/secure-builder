# © 2026 Casey Houle. All rights reserved.
"""Failure semantics (spec 01 §1.2, §13.1–13.2; spec 11 §5)."""
import unittest

from engine.outcome import Outcome, State, Summary


class OutcomeStates(unittest.TestCase):
    def test_six_states_have_distinct_wording(self):
        lines = {
            Outcome.clean("c", "d").line(), Outcome.found("c", "d", ["x"]).line(),
            Outcome.could_not_run("c", "d").line(),
            Outcome.not_applicable("c", "web", "d", "nothing").line(),
            Outcome.nothing_yet("c", "routes", "d").line(), Outcome.deferred("c", "budget", "d").line(),
        }
        self.assertEqual(len(lines), 6, lines)
        words = [l.split("] ", 1)[1].split(":")[0].split(" on ")[0].split(" (")[0] for l in lines]
        self.assertEqual(len(set(words)), 6, f"state wordings collide: {words}")

    def test_exit_codes(self):
        self.assertEqual(Outcome.clean("c", "d").exit_code, 0)
        self.assertEqual(Outcome.not_applicable("c", "s", "d", "nothing").exit_code, 0)
        self.assertEqual(Outcome.nothing_yet("c", "s", "d").exit_code, 0)
        self.assertEqual(Outcome.found("c", "d", ["f"]).exit_code, 1)
        self.assertEqual(Outcome.could_not_run("c", "d").exit_code, 2)
        self.assertEqual(Outcome.deferred("c", "budget", "d").exit_code, 3)

    def test_not_applicable_must_name_shape_and_coverage(self):
        with self.assertRaises(ValueError):
            Outcome(check="c", state=State.NOT_APPLICABLE, detail="d", shape="", covers="x")
        with self.assertRaises(ValueError):
            Outcome(check="c", state=State.NOT_APPLICABLE, detail="d", shape="android", covers="")
        line = Outcome.not_applicable("inj", "android", "reads JS/TS source only",
                                      "nothing — Kotlin persistence is unguarded").line()
        self.assertEqual(line, "[inj] NOT APPLICABLE on shape 'android': reads JS/TS source only "
                               "— covered instead by: nothing — Kotlin persistence is unguarded")

    def test_deferred_is_not_skipped_and_carries_reason(self):
        with self.assertRaises(ValueError):
            Outcome(check="c", state=State.DEFERRED, detail="d", reason="")
        line = Outcome.deferred("mutation", "budget", "3 controls unmutated").line()
        self.assertEqual(line, "[mutation] DEFERRED (reason: budget) — owed; 3 controls unmutated")
        self.assertNotIn("SKIP", line.upper())
        self.assertNotIn("NOT APPLICABLE", line)

    def test_findings_cannot_be_empty_and_only_findings_block(self):
        with self.assertRaises(ValueError):
            Outcome(check="c", state=State.FINDINGS, detail="d", findings=[])
        with self.assertRaises(ValueError):
            Outcome(check="c", state=State.CLEAN, detail="d", blocking=True)
        self.assertEqual(Outcome.found("c", "d", ["f"], blocking=True).line(),
                         "[c] FINDINGS BLOCKING: 1 finding(s) — d")

    def test_nothing_yet_is_distinct_from_not_applicable(self):
        a = Outcome.nothing_yet("neg", "routes", "no HTTP surface has been added").line()
        b = Outcome.not_applicable("neg", "library", "no HTTP surface by design", "nothing").line()
        self.assertTrue(a.startswith("[neg] NOTHING TO CHECK YET"), a)
        self.assertTrue(b.startswith("[neg] NOT APPLICABLE"), b)


class SummaryCounts(unittest.TestCase):
    def outcomes(self):
        return [Outcome.clean("a", "d"), Outcome.found("b", "d", ["f"]),
                Outcome.not_applicable("c", "s", "d", "nothing"), Outcome.could_not_run("e", "d"),
                Outcome.nothing_yet("f", "s", "d"), Outcome.deferred("g", "budget", "d")]

    def test_counts_reported_separately(self):
        s = Summary(self.outcomes())
        self.assertEqual(s.line(), "[summary] 6 checks: 4 applicable, 1 not applicable, "
                                   "1 nothing-yet, 1 deferred, 3 failed")
        self.assertEqual(s.exit_code, 3)

    def test_empty_suite_is_not_a_pass(self):
        s = Summary([])
        self.assertEqual(s.exit_code, 2)
        self.assertTrue(s.line().startswith("[summary] COULD NOT RUN: zero checks"), s.line())

    def test_na_over_threshold_is_a_nonblocking_finding(self):
        outs = [Outcome.not_applicable(f"n{i}", "android", "reads web source", "nothing") for i in range(3)]
        outs.append(Outcome.clean("ok", "d"))
        s = Summary(outs, na_threshold=0.5)
        self.assertTrue(s.na_over_threshold)
        self.assertEqual(s.exit_code, 0, "the threshold finding must not block")
        lines = s.disposition_lines()
        self.assertTrue(lines[0].startswith("[summary] FINDING (non-blocking, requires disposition): 3/4"), lines[0])
        self.assertIn("unguarded ground:", lines[0])
        self.assertEqual(len(lines), 4)

    def test_na_under_threshold_no_finding(self):
        s = Summary([Outcome.clean("a", "d"), Outcome.not_applicable("b", "s", "d", "x")], na_threshold=0.5)
        self.assertFalse(s.na_over_threshold)
        self.assertEqual(s.disposition_lines(), [])
