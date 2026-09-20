# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Generated system truth (spec 02 §9; spec 03 REQ-3.5.3)."""
import unittest

from engine import gate, truth
from engine.checks import generated_truth
from engine.outcome import State
from .helpers import commit, git, git_repo, tree, write

NL = chr(10)
APP = "@app.route('/items')" + NL + "def items(): pass" + NL + "class Item:" + NL + "    pass" + NL


def project(t):
    git_repo(t)
    write(t, "src/app.py", APP)
    write(t, "db/schema.sql", "CREATE TABLE items (id int);" + NL)
    commit(t, "c")


class Generation(unittest.TestCase):
    def test_generated_from_code_and_marked_never_hand_edited(self):
        with tree() as t:
            project(t)
            tr = truth.write(t)
            self.assertEqual([r["path"] for r in tr["routes"]], ["/items"])
            self.assertEqual(sorted(s["name"] for s in tr["structures"]), ["Item", "items"])
            text = (t / truth.FILE).read_text(encoding="utf-8")
            self.assertIn(truth.MARKER, text.splitlines())
            self.assertIn("- ANY /items (src/app.py:1)", text.splitlines())
            self.assertFalse(truth.hand_edited(t))

    def test_hand_edit_is_detected_and_regeneration_overwrites(self):
        with tree() as t:
            project(t)
            truth.write(t)
            p = t / truth.FILE
            p.write_text(p.read_text(encoding="utf-8").replace("- ANY /items", "- ANY /items-and-more"), encoding="utf-8")
            self.assertTrue(truth.hand_edited(t))
            generated_truth.run(t, None)
            self.assertFalse(truth.hand_edited(t), "the check regenerates; a hand edit never survives")


class Comparison(unittest.TestCase):
    def test_no_plan_is_nothing_yet(self):
        with tree() as t:
            project(t)
            self.assertIs(generated_truth.run(t, None).state, State.NOTHING_YET)

    def test_divergence_is_a_human_decision_never_reconciled(self):
        with tree() as t:
            project(t)
            write(t, "plans/design.md", "## Interfaces" + NL + "- ANY /items" + NL + "- POST /orders" + NL + "## Data" + NL + "- Item" + NL)
            o = generated_truth.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertFalse(o.blocking)
            self.assertEqual(o.findings, [
                "interface POST /orders: in plan, not in code — a human decision (revise the plan or change the code); ticket TRUTH-interface-POST-orders",
                "data items: in code, not in plan — a human decision (revise the plan or change the code); ticket TRUTH-data-items"])
            self.assertTrue((t / "tickets/TRUTH-interface-POST-orders.md").is_file())
            plan_after = (t / "plans/design.md").read_text(encoding="utf-8")
            self.assertIn("- POST /orders", plan_after, "the plan is never silently rewritten to match the code")
            self.assertNotIn("- items", plan_after, "the code's structures are never silently added to the plan")

    def test_match_is_clean(self):
        with tree() as t:
            project(t)
            write(t, "plans/design.md", "## Interfaces" + NL + "- ANY /items" + NL + "## Data" + NL + "- Item" + NL + "- items" + NL)
            self.assertIs(generated_truth.run(t, None).state, State.CLEAN)


class LoadBearing(unittest.TestCase):
    def test_negative_test_enumeration_uses_the_generated_inventory(self):
        import inspect
        self.assertIn("routes.inventory(", inspect.getsource(gate.negative_test_set))
