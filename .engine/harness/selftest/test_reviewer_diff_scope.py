# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The reviewer reads the project's code: vendored third-party files and bulk data are named, not
pasted (antipode A-2: minified Leaflet put the review at 47K tokens and it could not run)."""
import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWERS = ROOT / "reviewers" if (ROOT / "reviewers").is_dir() else ROOT.parent / "reviewers"


def load(name):
    spec = importlib.util.spec_from_file_location(name, REVIEWERS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


class DiffScope(unittest.TestCase):
    def test_vendored_and_bulk_files_are_named_not_pasted(self):
        lm = load("local_model")
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            git(root, "init", "-q")
            git(root, "config", "user.email", "t@example.invalid")
            git(root, "config", "user.name", "t")
            git(root, "config", "commit.gpgsign", "false")
            (root / "AGENTS.md").write_text("## Project rules\n\n1. none\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "base")
            base = git(root, "rev-parse", "HEAD")
            (root / "src" / "static" / "vendor" / "lib").mkdir(parents=True)
            (root / "src" / "static" / "vendor" / "lib" / "lib.js").write_text("var VENDORED_MARKER=1;\n", encoding="utf-8")
            (root / "src" / "static" / "world.geojson").write_text("BULK_MARKER" + "x" * 50_000 + "\n", encoding="utf-8")
            (root / "src" / "server.py").write_text("PROJECT_MARKER = 1\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "change")
            head = git(root, "rev-parse", "HEAD")
            prompt = lm.build_prompt(root, {"unit": "U1", "run": "1", "base": base, "head": head}, "checklist", "definition", [])
        self.assertIn("PROJECT_MARKER", prompt)
        self.assertNotIn("VENDORED_MARKER", prompt)
        self.assertNotIn("BULK_MARKER", prompt)
        self.assertIn("src/static/vendor/lib/lib.js", prompt)
        self.assertIn("vendored third-party", prompt)
        self.assertIn("bulk data", prompt)

    def test_binary_files_are_summarized_by_folder(self):
        lm = load("local_model")
        numstat = "\n".join(f"-\t-\tsrc/static/tiles/5/{i}/0.jpg" for i in range(50)) + "\n3\t1\tsrc/server.py\n"
        shown, held = lm.held_back_files(numstat)
        self.assertEqual(shown, ["src/server.py"])
        self.assertEqual(held, ["src/static/tiles/: 50 binary file(s), not shown"], "one line for the whole tile set")


if __name__ == "__main__":
    unittest.main()
