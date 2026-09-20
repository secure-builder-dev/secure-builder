# © 2026 Casey Houle. All rights reserved.
"""Configuration model (spec 01 §2; spec 04 §1)."""
import json
import unittest

from engine import config as cfgmod
from engine.outcome import State
from .helpers import tree, write, write_config


class Axes(unittest.TestCase):
    def test_stored_at_fixed_path(self):
        self.assertEqual(cfgmod.CONFIG_PATH, ".engine/config.json")
        with tree() as t:
            cfgmod.init(t, track="web", mode="local", tier="IL4", provider="aws")
            self.assertTrue((t / ".engine" / "config.json").is_file())

    def test_sentinel_blocks_gate(self):
        with tree() as t:
            write_config(t, provider="unset")
            o = cfgmod.check(t)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["axis 'provider' is not yet chosen"])

    def test_missing_config_is_blocking_not_silent(self):
        with tree() as t:
            o = cfgmod.check(t)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertIn("not initialized", o.detail)

    def test_malformed_config_could_not_run(self):
        with tree() as t:
            write(t, ".engine/config.json", "{not json")
            o = cfgmod.check(t)
            self.assertIs(o.state, State.COULD_NOT_RUN)

    def test_complete_config_is_clean_and_states_mode(self):
        with tree() as t:
            write_config(t)
            o = cfgmod.check(t)
            self.assertIs(o.state, State.CLEAN)
            self.assertIn("mode: local; topology: single; side: local", o.line())

    def test_android_forces_tier_and_provider(self):
        with tree() as t:
            cfg = cfgmod.init(t, track="android", mode="disconnected", app_type="atak")
            self.assertEqual((cfg.tier, cfg.provider), ("IL6", "tactical"))
            data = json.loads((t / ".engine/config.json").read_text())
            self.assertEqual(data["provider"], "tactical")

    def test_android_contradiction_is_a_problem(self):
        with tree() as t:
            write_config(t, track="android", tier="IL6", provider="aws", app_type="native")
            o = cfgmod.check(t)
            self.assertIs(o.state, State.FINDINGS)
            self.assertIn("track=android forces provider=tactical, but provider=aws", o.findings)

    def test_web_sets_app_type_na(self):
        with tree() as t:
            cfg = cfgmod.init(t, track="web", mode="connected", tier="IL4", provider="azure")
            self.assertEqual(cfg.app_type, "n/a")
            self.assertEqual(cfg.unset_axes(), [])

    def test_init_refuses_overwrite(self):
        with tree() as t:
            cfgmod.init(t, track="web", mode="local", tier="IL4", provider="aws")
            with self.assertRaises(cfgmod.ConfigError):
                cfgmod.init(t, track="android", mode="local", app_type="native")

    def test_unknown_value_rejected(self):
        with tree() as t:
            write_config(t, tier="IL9")
            self.assertIn("tier='IL9' is not one of ('IL4', 'IL6')", cfgmod.check(t).findings)


class Mode(unittest.TestCase):
    def test_mode_must_be_explicit(self):
        with tree() as t:
            with self.assertRaises(cfgmod.ConfigError) as cm:
                cfgmod.init(t, track="web", mode="auto", tier="IL4", provider="aws")
            self.assertIn("never inferred", str(cm.exception))

    def test_unset_mode_blocks(self):
        with tree() as t:
            write_config(t, mode="unset")
            o = cfgmod.check(t)
            self.assertIs(o.state, State.FINDINGS)
            self.assertIn("axis 'mode' is not yet chosen", o.findings)

    def test_three_modes_only(self):
        self.assertEqual(cfgmod.MODES, ("connected", "local", "disconnected"))
        with tree() as t:
            write_config(t, mode="field")
            self.assertIn("mode='field' is not one of ('connected', 'local', 'disconnected')",
                          cfgmod.check(t).findings)

    def test_topology_and_side(self):
        self.assertEqual(cfgmod.TOPOLOGIES, ("single", "low-side", "high-side"))
        with tree() as t:
            write_config(t, topology="high-side", side="HIGH")
            o = cfgmod.check(t)
            self.assertIs(o.state, State.CLEAN)
            self.assertIn("topology: high-side; side: HIGH", o.line())
            write_config(t, topology="mirror")
            self.assertIn("topology='mirror' is not one of ('single', 'low-side', 'high-side')",
                          cfgmod.check(t).findings)
