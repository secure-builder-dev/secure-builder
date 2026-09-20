# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The network door (spec 04 REQ-2.2, REQ-3.4; spec 01 REQ-8.4.1)."""
import unittest

from engine import net
from engine.checks import no_network
from engine.outcome import State
from .helpers import ROOT, tree, write


class Door(unittest.TestCase):
    def test_only_three_callers(self):
        self.assertEqual(net.ALLOWED_CALLERS, {"currency", "scanner-images", "detection-data"})
        self.assertIn("not permitted to reach the network", net.permitted("connected", "gate"))

    def test_disconnected_is_an_error_not_a_fallback(self):
        why = net.permitted("disconnected", "currency")
        self.assertEqual(why, "mode is disconnected: 'currency' must not attempt a connection (use the offline path)")
        with self.assertRaises(net.NetworkForbidden):
            net.fetch("http://127.0.0.1:9/", mode="disconnected", caller="currency")

    def test_unknown_mode_refuses_to_infer(self):
        self.assertIn("refusing to infer", net.permitted("unset", "currency"))

    def test_permitted_callers_in_connected_and_local(self):
        for mode in ("connected", "local"):
            for c in net.ALLOWED_CALLERS:
                self.assertIsNone(net.permitted(mode, c))


class SelfScan(unittest.TestCase):
    def test_harness_source_is_clean(self):
        o = no_network.run(ROOT, None)
        self.assertIs(o.state, State.CLEAN, o.line())
        self.assertRegex(o.line(), r"^\[no-network\] CLEAN: \d+ harness modules import no network library outside net\.py$")

    def test_direct_import_in_harness_module_is_blocking(self):
        with tree() as t:
            write(t, "engine/checks/__init__.py", "")
            write(t, "engine/net.py", "import urllib.request" + chr(10))
            write(t, "engine/sneaky.py", "import socket" + chr(10))
            o = no_network.run(t, None)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["engine/sneaky.py:1: import socket"])

    def test_no_harness_tree_could_not_run(self):
        with tree() as t:
            self.assertIs(no_network.run(t, None).state, State.COULD_NOT_RUN)

    def test_forbidden_pattern_catches_direct_imports(self):
        for line in ("import socket", "from urllib import request", "import http.client", "import ssl"):
            self.assertTrue(no_network.FORBIDDEN.match(line), line)
        self.assertFalse(no_network.FORBIDDEN.match("from .outcome import Outcome"))
        self.assertFalse(no_network.FORBIDDEN.match("import hashlib"))
