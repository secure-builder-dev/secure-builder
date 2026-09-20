# © 2026 Casey Houle. All rights reserved.
"""Fixtures for the build's hooks (spec 07 §6) — enforcement outside the
assistant's judgment has to be shown refusing what it must refuse.
Each test builds a throwaway git repository carrying a copy of the hook, a stub
engine package whose `check` exits as the test chooses, and stages a file.
Run: python tools/hooks_test.py"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
HEADER = "© 2026 Casey Houle. All rights reserved."
NL = chr(10)
TAB = chr(9)


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


class HookRepo(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="hooks-fx-"))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=self.root)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=self.root)
        shutil.copy(HERE.parent / "hooks" / "pre-commit.py", self.root / "pre-commit.py")
        shutil.copy(HERE.parent / "hooks" / "commit-msg.py", self.root / "commit-msg.py")
        (self.root / "tools").mkdir()
        shutil.copy(HERE / "progress.py", self.root / "tools" / "progress.py")
        write(self.root, "specs/01-X.md", "## 1. S\n\n**REQ-1.1** It MUST.\n")
        write(self.root, "ledger.tsv", "req\tspec\tstage\tstatus\timpl\treceipt\tnote\n"
              "REQ-1.1\t01\t1\ttodo\t-\t-\t\n")
        write(self.root, ".journal/.keep", "")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def engine(self, exit_code):
        write(self.root, "engine/__init__.py", "")
        write(self.root, "engine/__main__.py", f"import sys\nprint('stub check')\nsys.exit({exit_code})\n")

    def stage(self, rel, text):
        write(self.root, rel, text)
        subprocess.run(["git", "add", rel], cwd=self.root, check=True)

    def pre_commit(self, env=None):
        e = dict(os.environ)
        e.pop("ENGINE_GOVERNANCE_OK", None)
        if env:
            e.update(env)
        res = subprocess.run([sys.executable, "pre-commit.py"], cwd=self.root, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", env=e)
        return res.returncode, res.stdout.splitlines()

    def commit_msg(self, message):
        write(self.root, "MSG", message)
        res = subprocess.run([sys.executable, "commit-msg.py", "MSG"], cwd=self.root, capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
        return res.returncode, res.stdout.strip()

    # --- the five refusals ---

    def test_red_check_refused(self):
        self.engine(1)
        self.stage("src/x.py", f"# {HEADER}\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 1)
        self.assertIn("pre-commit: REFUSED", lines)
        self.assertTrue(any(l.startswith("  - `python -m engine check` is red (exit 1)") for l in lines), lines)

    def test_green_check_accepted(self):
        self.engine(0)
        self.stage("src/x.py", f"# {HEADER}\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 0, lines)
        self.assertIn("pre-commit: check green", lines)

    def test_governance_file_refused_without_approval_and_logged_with_it(self):
        self.engine(0)
        self.stage("v1.0.md", f"# {HEADER}\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith("  - governance set touched without ENGINE_GOVERNANCE_OK=1: v1.0.md") for l in lines), lines)
        rc, lines = self.pre_commit({"ENGINE_GOVERNANCE_OK": "1"})
        self.assertEqual(rc, 0, lines)
        self.assertIn("v1.0.md", (self.root / ".journal/governance").read_text(encoding="utf-8"))

    def test_assistant_name_in_file_refused(self):
        self.engine(0)
        name = "Cla" + "ude"   # split so this source file never carries the name itself
        self.stage("notes.md", f"{HEADER}\nDrafted with help from {name}.\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 1)
        self.assertTrue(any("assistant attribution or name in notes.md" in l for l in lines), lines)

    def test_missing_header_refused(self):
        self.engine(0)
        self.stage("src/y.py", "x = 1\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 1)
        self.assertIn("  - missing copyright header: src/y.py", lines)

    def test_false_done_row_refused(self):
        self.engine(0)
        write(self.root, "ledger.tsv", "req\tspec\tstage\tstatus\timpl\treceipt\tnote\n"
              "REQ-1.1\t01\t1\tdone\tengine/nope.py\treceipts/none.txt\t\n")
        self.stage("src/x.py", f"# {HEADER}\n")
        rc, lines = self.pre_commit()
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith("  - ledger claims done falsely:") for l in lines), lines)

    def test_commit_msg_refuses_trailer_and_name(self):
        trailer = "Co-Authored" + "-By"   # split so this source file never carries the trailer itself
        rc, out = self.commit_msg(f"fix: thing\n\n{trailer}: Someone <x@y>\n")
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith("commit-msg: REFUSED"), out)
        rc, out = self.commit_msg("fix: thing\n")
        self.assertEqual((rc, out), (0, ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
