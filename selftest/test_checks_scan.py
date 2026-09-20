# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Credential scan, injection scan, harness self-scan (spec 01 §10, REQ-10.2, 10.3, 10.6, §13.2)."""
import unittest

from engine.checks import credential_scan, harness_self_scan, injection_scan
from engine.config import Config
from engine.outcome import State
from .helpers import ROOT, cli, find_line, git, git_repo, tree, write

WEB = Config({"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local"})
ANDROID = Config({"schema": 1, "track": "android", "tier": "IL6", "provider": "tactical", "app_type": "native", "mode": "local"})
KEY = "AKIA" + "ABCDEFGHIJKLMNOP"   # assembled so this file does not itself trip the scan


class CredentialScan(unittest.TestCase):
    def test_credential_in_tracked_file_is_blocking(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/cfg.py", f"AWS_KEY = '{KEY}'" + chr(10))
            git(t, "add", "-A")
            o = credential_scan.run(t, WEB)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["src/cfg.py:1: AWS access key id"])

    def test_assigned_secret_detected_and_placeholder_skipped(self):
        self.assertEqual(credential_scan.scan_text("a.py", 'password = "hunter2hunter2"'), ["a.py:1: assigned secret"])  # engine:allow-credential
        self.assertEqual(credential_scan.scan_text("a.py", 'password = "<your-password>"'), [])
        self.assertEqual(credential_scan.scan_text("a.py", 'password = "changeme"'), [])
        self.assertEqual(credential_scan.scan_text("a.py", 'password = os.environ["DB_PASSWORD"]'), [])

    def test_inline_allow_annotation(self):
        self.assertEqual(credential_scan.scan_text("a.py", f'k = "{KEY}"  # engine:allow-credential'), [])

    def test_example_and_template_files_skipped(self):
        self.assertEqual(credential_scan.scan_text("config.yml.example", f'key: {KEY}'), [])
        self.assertEqual(credential_scan.scan_text("templates/x.yml", f'key: {KEY}'), [])
        self.assertEqual(credential_scan.scan_text("config.yml", f'key: {KEY}'), ["config.yml:1: AWS access key id"])

    def test_private_key_block(self):
        self.assertEqual(credential_scan.scan_text("id", "-----BEGIN OPENSSH PRIVATE KEY-----"), ["id:1: private key"])  # engine:allow-credential

    def test_clean_tree(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/a.py", "x = 1" + chr(10))
            git(t, "add", "-A")
            o = credential_scan.run(t, WEB)
            self.assertIs(o.state, State.CLEAN)
            self.assertEqual(o.line(), "[credential-scan] CLEAN: 1 tracked files carry no credential-shaped content")

    def test_nothing_readable_could_not_run(self):
        with tree() as t:
            self.assertIs(credential_scan.run(t, WEB).state, State.COULD_NOT_RUN)

    def test_same_definition_against_staged_index(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/cfg.py", f"AWS_KEY = '{KEY}'" + chr(10))
            git(t, "add", "-A")
            scanned, findings = credential_scan.scan_staged(t)
            self.assertEqual((scanned, findings), (1, ["src/cfg.py:1: AWS access key id"]))
            code, lines = cli(t, "credential-scan", "--staged")
            self.assertEqual(code, 1)
            find_line(lines, "[credential-scan] staged: 1 file(s), 1 finding(s)")


class InjectionScan(unittest.TestCase):
    def test_concatenated_sql_is_blocking(self):
        with tree() as t:
            git_repo(t)
            write(t, "src/db.py", 'cur.execute("SELECT * FROM users WHERE id = " + user_id)' + chr(10))
            git(t, "add", "-A")
            o = injection_scan.run(t, WEB)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["src/db.py:1: concatenated SQL"])

    def test_fstring_and_template_literal(self):
        self.assertEqual(injection_scan.scan_text("a.py", 'cur.execute(f"SELECT * FROM t WHERE id = {uid}")'), ["a.py:1: f-string SQL"])
        self.assertEqual(injection_scan.scan_text("a.js", 'db.query(`SELECT * FROM t WHERE id = ${id}`)'), ["a.js:1: template-literal SQL"])
        self.assertEqual(injection_scan.scan_text("a.py", 'cur.execute("SELECT * FROM t WHERE id = %s", (uid,))'), [])

    def test_android_track_is_not_applicable_and_names_the_gap(self):
        with tree() as t:
            o = injection_scan.run(t, ANDROID)
            self.assertIs(o.state, State.NOT_APPLICABLE)
            self.assertEqual(o.line(), "[injection-scan] NOT APPLICABLE on shape 'track=android': this scanner reads "
                                       "JavaScript/TypeScript and Python source for string-built queries — covered instead by: "
                                       "nothing — persistence code in this track's language is checked by no injection scan")

    def test_no_source_yet(self):
        with tree() as t:
            git_repo(t)
            write(t, "README.md", "hi" + chr(10))
            git(t, "add", "-A")
            self.assertIs(injection_scan.run(t, WEB).state, State.NOTHING_YET)

    def test_test_files_excluded(self):
        with tree() as t:
            git_repo(t)
            write(t, "tests/test_db.py", 'cur.execute("SELECT * FROM t WHERE id = " + x)' + chr(10))
            write(t, "src/ok.py", "x = 1" + chr(10))
            git(t, "add", "-A")
            self.assertIs(injection_scan.run(t, WEB).state, State.CLEAN)


class HarnessSelfScan(unittest.TestCase):
    def test_real_harness_is_clean(self):
        o = harness_self_scan.run(ROOT, WEB)
        self.assertIs(o.state, State.CLEAN, o.lines())

    def test_third_party_import_is_blocking(self):
        with tree() as t:
            write(t, "engine/checks/__init__.py", "")
            write(t, "engine/net.py", "")
            write(t, "engine/extra.py", "import requests" + chr(10))
            o = harness_self_scan.run(t, WEB)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["engine/extra.py: imports third-party module 'requests'"])

    def test_credential_in_harness_source_is_blocking(self):
        with tree() as t:
            write(t, "engine/checks/__init__.py", "")
            write(t, "engine/net.py", f"TOKEN = '{KEY}'" + chr(10))
            o = harness_self_scan.run(t, WEB)
            self.assertIs(o.state, State.FINDINGS)
            self.assertEqual(o.findings, ["harness engine/net.py:1: AWS access key id"])

    def test_vendored_data_hash_mismatch_is_blocking(self):
        with tree() as t:
            write(t, "engine/checks/__init__.py", "")
            write(t, ".engine/catalogues/cat.json", "{}")
            write(t, ".engine/catalogues/cat.provenance.json", '{"file": "cat.json", "sha256": "0000"}')
            o = harness_self_scan.run(t, WEB)
            self.assertIs(o.state, State.FINDINGS)
            self.assertEqual(o.findings, ["cat.json: content hash differs from its recorded provenance"])

    def test_no_harness_tree_could_not_run(self):
        with tree() as t:
            self.assertIs(harness_self_scan.run(t, WEB).state, State.COULD_NOT_RUN)
