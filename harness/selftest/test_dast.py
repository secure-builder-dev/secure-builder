# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The running server probed from outside, against real servers started for the test."""
import json
import sys
import unittest

from engine.scan import dast, runner
from .helpers import commit, git_repo, tree, write
from .test_scan import Fake, baseline, cfg

BAD = '''import sys, traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/%ff"):
            body = traceback.format_exc() + 'Traceback (most recent call last):\\n  File "app.py", line 9, in do_GET\\n'
            self.send_response(500); self.end_headers(); self.wfile.write(body.encode()); return
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(b"<p>hi</p>")
    def do_POST(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
'''
GOOD = '''import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class H(BaseHTTPRequestHandler):
    timeout = 5
    def log_message(self, *a): pass
    def _send(self, code, body=b"ok", ctype="text/html"):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Security-Policy", "default-src 'self'"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path.startswith("/api/secret"): return self._send(401, b"no")
        self._send(200 if self.path == "/" else 404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 65536: return self._send(413, b"too large")
        self.rfile.read(n); self._send(401 if self.path.startswith("/api/secret") else 400, b"bad request")
    do_PUT = do_POST
s = ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H); s.daemon_threads = True; s.serve_forever()
'''


class Probe(unittest.TestCase):
    def run_probe(self, code, protected=()):
        with tree() as t:
            write(t, "app.py", code)
            problems, found = dast.probe(t, [sys.executable, "app.py", "{port}"], protected, start_timeout=15)
        return problems, {r: s for r, s, _, _ in found}

    def test_a_bad_server_is_caught(self):
        problems, found = self.run_probe(BAD, protected=["/api/secret"])
        self.assertEqual(problems, [])
        self.assertEqual(found.get("dast-idle-connection-blocks"), "HIGH")
        self.assertEqual(found.get("dast-stack-trace-leak"), "HIGH")
        self.assertEqual(found.get("dast-protected-route-open"), "HIGH")
        self.assertEqual(found.get("dast-no-content-security-policy"), "MEDIUM")

    def test_a_good_server_passes(self):
        problems, found = self.run_probe(GOOD, protected=["/api/secret"])
        self.assertEqual((problems, found), ([], {}))

    def test_a_server_that_never_answers_is_a_problem(self):
        with tree() as t:
            write(t, "app.py", "import sys; sys.exit(3)\n")
            problems, found = dast.probe(t, [sys.executable, "app.py"], start_timeout=5)
        self.assertTrue(problems and "did not answer" in problems[0] and "the scan fails" in problems[0], problems)

    def test_a_command_that_cannot_start_is_a_problem(self):
        with tree() as t:
            problems, _ = dast.probe(t, ["no-such-program-xyz"], start_timeout=2)
        self.assertTrue(problems[0].startswith("dast: serve_command could not start"), problems)


class Detection(unittest.TestCase):
    def test_server_code_is_recognized(self):
        with tree() as t:
            write(t, "a.py", "from http.server import ThreadingHTTPServer\n")
            write(t, "b.py", "import json\n")
            write(t, "c.js", "const express = require('express');\n")
            self.assertTrue(dast.is_server([t / "a.py"], []))
            self.assertFalse(dast.is_server([t / "b.py"], []))
            self.assertTrue(dast.is_server([t / "c.js"], []))
            self.assertTrue(dast.is_server([], [("flows.json", [])]))

    def test_the_scan_requires_a_serve_command_for_a_server(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/app.py", "from http.server import ThreadingHTTPServer\n")
            commit(t, "server")
            r = runner.Scan(t, cfg(ship_images={}), invoke=Fake(baseline(vulns=False)), engine=("containers", "docker")).run()
        self.assertEqual(r["verdict"], "red")
        self.assertTrue(any("declares no serve_command" in p for p in r["problems"]), r["problems"])
        self.assertNotIn("dast", r["ran"])

    def test_the_scan_probes_a_declared_server_and_gates_on_it(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/app.py", BAD)
            commit(t, "server")
            c = cfg(ship_images={}, serve_command=[sys.executable, "src/app.py", "{port}"])
            r = runner.Scan(t, c, invoke=Fake(baseline(vulns=False)), engine=("containers", "docker")).run()
        self.assertIn("dast", r["ran"])
        self.assertEqual(r["verdict"], "red")
        self.assertIn("dast-idle-connection-blocks", [f.id for f in r["actionable"]])
