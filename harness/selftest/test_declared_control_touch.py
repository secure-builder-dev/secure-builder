# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A change inside a declared control's own function is control-shaped, whatever words it uses (daynight
probe: 'unsafe-inline' added inside csp_for passed the mechanical gate as not control-shaped)."""
import json
import pathlib
import subprocess
import tempfile
import unittest

from engine import gate

SRC = "def csp_for(page):\n    return \"script-src 'self'\"\n\n\ndef other():\n    return 1\n"
MANIFEST = {"schema": 1, "controls": [{"id": "SC-18", "description": "policy", "location": {"file": "src/s.py", "symbol": "csp_for"},
                                         "required_artifact": None, "test_pattern": "tests/test_*", "status": "system-specific",
                                         "counterpart": None, "mutation": None}]}


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


class DeclaredControlTouched(unittest.TestCase):
    def repo(self, d, new_src):
        root = pathlib.Path(d)
        git(root, "init", "-q")
        git(root, "config", "user.email", "t@example.invalid")
        git(root, "config", "user.name", "t")
        git(root, "config", "commit.gpgsign", "false")
        (root / "src").mkdir()
        (root / ".engine" / "rules").mkdir(parents=True)
        (root / ".engine" / "rules" / "control-manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
        (root / "src" / "s.py").write_text(SRC, encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "base")
        base = git(root, "rev-parse", "HEAD")
        (root / "src" / "s.py").write_text(new_src, encoding="utf-8")
        git(root, "commit", "-qam", "change")
        return root, base, git(root, "rev-parse", "HEAD")

    def test_an_edit_inside_the_control_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root, base, head = self.repo(d, SRC.replace("'self'", "'self' 'unsafe-inline'"))
            self.assertEqual(gate.declared_controls_touched(root, base, head), ["SC-18"])

    def test_an_edit_outside_the_control_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            root, base, head = self.repo(d, SRC.replace("return 1", "return 2"))
            self.assertEqual(gate.declared_controls_touched(root, base, head), [])


if __name__ == "__main__":
    unittest.main()
