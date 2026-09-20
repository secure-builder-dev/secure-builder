# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The pre-execution guard blocks exactly three commands and nothing else (spec 03 §4)."""
import unittest

from engine import guard


class Blocks(unittest.TestCase):
    def test_push_to_protected_branch(self):
        self.assertEqual(guard.blocks("git push origin main", "main", "feature"), "push to protected branch 'main'")
        self.assertEqual(guard.blocks("git push origin feature:main", "main", "feature"), "push to protected branch 'main'")
        self.assertEqual(guard.blocks("git push", "main", "main"), "push from protected branch 'main' (would update it)")
        self.assertEqual(guard.blocks("git -C /repo push --force origin main", "main", "x"), "push to protected branch 'main'")

    def test_merge_while_on_protected_branch(self):
        self.assertEqual(guard.blocks("git merge feature", "main", "main"), "merge while on protected branch 'main'")

    def test_remote_merge(self):
        self.assertEqual(guard.blocks("gh pr merge 42 --squash", "main", "feature"), "remote merge via the hosting platform")


class Allows(unittest.TestCase):
    def test_everything_else_is_allowed(self):
        for cmd in ("git push origin feature", "git push -u origin feature", "git merge main", "git status",
                    "git commit -m x", "gh pr create --fill", "gh pr view 42", "npm test", "git push origin :feature",
                    "git fetch origin main", "git rebase main", ""):
            self.assertIsNone(guard.blocks(cmd, "main", "feature"), cmd)

    def test_merge_off_protected_branch_allowed(self):
        self.assertIsNone(guard.blocks("git merge main", "main", "feature"))

    def test_other_protected_branch_name(self):
        self.assertEqual(guard.blocks("git push origin release", "release", "f"), "push to protected branch 'release'")
        self.assertIsNone(guard.blocks("git push origin main", "release", "f"))


class PlacedHook(unittest.TestCase):
    def test_placed_guard_refuses_and_allows(self):
        import subprocess, sys
        from engine import distribute
        from .helpers import commit, git_repo, tree, write_config
        with tree() as t:
            write_config(t, protected_branch="main")
            git_repo(t); commit(t)
            distribute.update(t)
            hook = t / ".engine" / "hooks" / "guard.py"
            res = subprocess.run([sys.executable, str(hook), "check", "git push origin main"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertTrue(res.stdout.startswith("guard: REFUSED"), res.stdout)
            res = subprocess.run([sys.executable, str(hook), "check", "git push origin feature"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            res = subprocess.run([sys.executable, str(hook), "pre-push", "origin", "url"], capture_output=True, text=True,
                                 input="refs/heads/feature abc refs/heads/main def" + chr(10))
            self.assertEqual(res.returncode, 1)
