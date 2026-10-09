# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A route the project declares public by design needs a test that it never refuses, not a test that
it refuses (antipode: a public, stateless API satisfied the credential check only because a test
happened to contain the word 401)."""
import unittest
from unittest import mock

from engine import gate


class Cfg(dict):
    pass


ROUTE = [{"method": "GET", "path": "/api/terminator", "file": "src/app.py", "line": 9, "record_scoped": False}]
NEVER_REFUSES = "def test_public(self):\n    status = get('/api/terminator')\n    self.assertNotIn(status, (401, 403))\n"
ONLY_200 = "def test_ok(self):\n    status = get('/api/terminator')\n    self.assertEqual(status, 200)\n"
REFUSES = "def test_auth(self):\n    status = get('/api/terminator')\n    self.assertEqual(status, 401)\n"


def run(cfg, tests):
    with mock.patch.object(gate.routes, "inventory", return_value=ROUTE), \
            mock.patch.object(gate.routes, "privileged_operations", return_value=[]), \
            mock.patch.object(gate.gitutil, "changed_files", return_value=["src/app.py"]), \
            mock.patch.object(gate, "_test_texts", return_value={"tests/test_t.py": tests}):
        return gate.negative_test_set(".", cfg, "a", "b")


class PublicRoutes(unittest.TestCase):
    def test_declared_public_and_shown_never_to_refuse_is_clean(self):
        out = run(Cfg(public_routes=["GET /api/terminator"]), NEVER_REFUSES)
        self.assertFalse(out.failed, out.lines())
        self.assertIn("1 declared public", " ".join(out.lines()))

    def test_declared_public_without_the_never_refuses_test_is_a_blocking_finding(self):
        out = run(Cfg(public_routes=["GET /api/terminator"]), ONLY_200)
        self.assertTrue(out.failed)
        self.assertIn("declared public, and no test asserts it never answers 401 or 403", " ".join(out.lines()))

    def test_an_undeclared_route_still_needs_its_rejection_test(self):
        self.assertTrue(run(Cfg(), NEVER_REFUSES).failed)
        self.assertFalse(run(Cfg(), REFUSES).failed)

    def test_a_rejection_word_in_a_comment_is_not_a_rejection_test(self):
        commented = "def test_ok(self):\n    status = get('/api/terminator')  # should be 401 without a token\n    self.assertEqual(status, 200)\n"
        self.assertTrue(run(Cfg(), commented).failed)

    def test_is_public_reads_method_and_path(self):
        cfg = Cfg(public_routes=["GET /api/terminator"])
        self.assertTrue(gate.is_public(cfg, "get", "/api/terminator"))
        self.assertFalse(gate.is_public(cfg, "POST", "/api/terminator"))
        self.assertFalse(gate.is_public(None, "GET", "/api/terminator"))


if __name__ == "__main__":
    unittest.main()
