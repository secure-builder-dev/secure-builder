# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""init sets the test and lint commands and the public routes (every demo hand-edited them in after init)."""
import json
import unittest

from selftest import helpers


class InitCommands(unittest.TestCase):
    def test_init_writes_the_commands_and_public_routes(self):
        with helpers.tree() as root:
            code, lines = helpers.cli(root, "init", "track=web", "mode=local", "tier=IL4", "provider=aws", "app_type=n/a",
                                      "test_command=python -m unittest discover -s tests -t .",
                                      "lint_command=python -m compileall -q src",
                                      "public_routes=GET /api/terminator, GET /api/x")
            self.assertEqual(code, 0, lines)
            data = json.loads((root / ".engine" / "rules" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["test_command"], ["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."])
        self.assertEqual(data["lint_command"], ["python", "-m", "compileall", "-q", "src"])
        self.assertEqual(data["public_routes"], ["GET /api/terminator", "GET /api/x"])

    def test_omitted_commands_are_absent(self):
        with helpers.tree() as root:
            helpers.cli(root, "init", "track=web", "mode=local", "tier=IL4", "provider=aws", "app_type=n/a")
            data = json.loads((root / ".engine" / "rules" / "config.json").read_text(encoding="utf-8"))
        for k in ("test_command", "lint_command", "public_routes"):
            self.assertNotIn(k, data)


if __name__ == "__main__":
    unittest.main()
