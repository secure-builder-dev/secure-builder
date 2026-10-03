# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A control implemented as a framework callback (do_GET, log_request on a BaseHTTPRequestHandler
subclass) is called by the server, not by a project line; and an override's super() call of itself is
not a call site (antipode: the static allowlist in do_GET could not be declared)."""
import pathlib
import tempfile
import unittest

from engine import manifest

SERVER = '''from http.server import BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)

    def end_headers(self):
        super().end_headers()

    def helper_nobody_calls(self):
        return 1
'''


class FrameworkCallbacks(unittest.TestCase):
    def sites(self, symbol):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "src").mkdir()
            (root / "src" / "server.py").write_text(SERVER, encoding="utf-8")
            return manifest.call_sites(root, symbol, "src/server.py")

    def test_an_override_of_a_framework_method_is_called_by_the_framework(self):
        sites = self.sites("do_GET")
        self.assertTrue(any("framework callback of BaseHTTPRequestHandler.do_GET" in s for s in sites), sites)

    def test_super_call_of_itself_is_not_a_call_site(self):
        sites = self.sites("end_headers")
        self.assertFalse(any(s.endswith(":9") for s in sites), sites)
        self.assertTrue(any("framework callback" in s for s in sites), sites)

    def test_a_method_the_framework_does_not_define_is_still_uncalled(self):
        self.assertEqual(self.sites("helper_nobody_calls"), [])


if __name__ == "__main__":
    unittest.main()
