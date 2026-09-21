# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""External tool invocation, stubbed on the search path (spec 05 §5; REQ-4.2)."""
import unittest

from engine import tools
from .helpers import tree
from .stubs import invocations, stub_path, stub_tool


class Stubbing(unittest.TestCase):
    def test_stub_shadows_tool_and_records_invocation(self):
        with tree() as t:
            stub_tool(t, "scanner-x", exit_code=0, stdout="clean\n")
            res = tools.run_tool("scanner-x", ["--image", "app:1"], path=stub_path(t))
            self.assertTrue(res.ran)
            self.assertEqual(res.exit_code, 0)
            self.assertEqual(res.stdout, "clean\n")
            self.assertEqual(invocations(t), ["scanner-x --image app:1"])

    def test_exit_code_is_exact_not_a_class(self):
        with tree() as t:
            stub_tool(t, "malware-y", exit_code=125, stdout="", stderr="container failed to start\n")
            res = tools.run_tool("malware-y", ["scan"], path=stub_path(t))
            self.assertEqual(res.exit_code, 125, "125 is 'the tool fell over', never 'detection'")
            self.assertNotEqual(res.exit_code, 1)
            stub_tool(t, "malware-z", exit_code=1, stdout="Infected files: 1\n")
            res = tools.run_tool("malware-z", ["scan"], path=stub_path(t))
            self.assertEqual(res.exit_code, 1)

    def test_missing_tool_is_reported_not_clean(self):
        with tree() as t:
            res = tools.run_tool("no-such-tool-anywhere", [], path=str(t))
            self.assertFalse(res.ran)
            self.assertEqual(res.exit_code, -1)
            self.assertEqual(res.stderr, "no-such-tool-anywhere: not found on the search path")

    def test_resolve_honours_given_path_only(self):
        with tree() as t:
            stub_tool(t, "only-here")
            self.assertTrue(tools.resolve("only-here", path=stub_path(t)))
            self.assertEqual(tools.resolve("only-here", path=""), "")

    def test_multiple_invocations_recorded_in_order(self):
        with tree() as t:
            stub_tool(t, "git-like")
            for args in (["a"], ["b", "c"]):
                tools.run_tool("git-like", args, path=stub_path(t))
            self.assertEqual(invocations(t), ["git-like a", "git-like b c"])


class Fixtures(unittest.TestCase):
    def test_throwaway_tree_is_removed_afterwards(self):
        with tree() as t:
            kept = t
            (t / "f").write_text("x")
            self.assertTrue(kept.exists())
        self.assertFalse(kept.exists(), "a fixture tree must not outlive its test")
