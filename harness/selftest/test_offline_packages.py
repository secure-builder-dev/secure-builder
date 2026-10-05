# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Third-party packages pinned by hash and held where the project builds disconnected."""
import base64
import hashlib
import json
import types
import unittest

from engine.scan import offline
from .helpers import cli, tree, write, write_config

NL = chr(10)


def files(t):
    return [p for p in t.rglob("*") if p.is_file() and "offline-packages" not in p.parts]


class Python(unittest.TestCase):
    def test_pins_need_hashes_and_a_held_file(self):
        with tree() as t:
            write(t, "offline-packages/idna-3.7-py3-none-any.whl", "wheel bytes")
            good = hashlib.sha256(b"wheel bytes").hexdigest()
            write(t, "requirements.txt", NL.join([
                f"idna==3.7 \\\\", f"    --hash=sha256:{good}",
                "requests==2.31.0", f"urllib3==2.2.2 --hash=sha256:{'0' * 64}", "-r other.txt", "# comment"]) + NL)
            got = offline.problems(t, files(t))
        self.assertEqual(len(got), 2, got)
        self.assertIn("requirements.txt: 'requests==2.31.0' carries no --hash", got[0])
        self.assertIn("urllib3==2.2.2 is not in offline-packages/ with a matching hash", got[1])

    def test_no_offline_source_at_all_is_one_problem_first(self):
        with tree() as t:
            write(t, "requirements.txt", f"idna==3.7 --hash=sha256:{'a' * 64}" + NL)
            got = offline.problems(t, files(t))
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].startswith("third-party packages with no offline package source (offline-packages/)"))

    def test_a_stdlib_project_needs_nothing(self):
        with tree() as t:
            write(t, "src/app.py", "import json" + NL)
            self.assertEqual(offline.problems(t, files(t)), [])

    def test_lock_pins_every_downloaded_distribution(self):
        with tree() as t:
            write(t, "requirements.in", "requests==2.31.0" + NL)

            def run(cmd, **kw):
                src = t / "offline-packages"
                (src / "requests-2.31.0-py3-none-any.whl").write_bytes(b"r")
                (src / "idna-3.7-py3-none-any.whl").write_bytes(b"i")
                (src / "charset_normalizer-3.3.2.tar.gz").write_bytes(b"c")
                self.assertIn("download", cmd)
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")
            ok, msg = offline.lock_python(t, "requirements.in", "requirements.txt", run=run)
            text = (t / "requirements.txt").read_text(encoding="utf-8")
            self.assertTrue(ok, msg)
            self.assertIn("3 distribution(s)", msg)
            self.assertIn("charset-normalizer==3.3.2", text)
            self.assertIn(f"--hash=sha256:{hashlib.sha256(b'i').hexdigest()}", text)
            self.assertEqual(offline.problems(t, files(t)), [], "what lock writes, the gate accepts")
            failed = offline.lock_python(t, "requirements.in", "x.txt",
                                         run=lambda c, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="no network"))
            self.assertEqual(failed, (False, "no network"))


class Npm(unittest.TestCase):
    def lock(self, t, integrity):
        entry = {"version": "4.17.21", "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"}
        if integrity:
            entry["integrity"] = integrity
        write(t, "package-lock.json", json.dumps({"lockfileVersion": 3, "packages": {
            "": {"name": "p"}, "node_modules/lodash": entry, "node_modules/local": {"version": "1.0.0", "resolved": "file:../x"},
            "node_modules/linked": {"link": True}}}))

    def test_integrity_is_required_and_held_in_the_cache(self):
        digest = hashlib.sha512(b"tgz").digest()
        integrity = "sha512-" + base64.b64encode(digest).decode()
        with tree() as t:
            self.lock(t, None)
            write(t, "offline-packages/README", "x")
            got = offline.problems(t, files(t))
            self.assertEqual(got, ["package-lock.json: lodash@4.17.21 has no integrity hash: npm cannot verify what it installs"])
        with tree() as t:
            self.lock(t, integrity)
            write(t, "offline-packages/README", "x")
            self.assertIn("lodash@4.17.21 is not in offline-packages/npm-cache", offline.problems(t, files(t))[0])
            h = digest.hex()
            write(t, f"offline-packages/npm-cache/content-v2/sha512/{h[:2]}/{h[2:4]}/{h[4:]}", "tgz")
            self.assertEqual(offline.problems(t, files(t)), [])

    def test_v1_lockfiles_are_read(self):
        with tree() as t:
            write(t, "package-lock.json", json.dumps({"lockfileVersion": 1, "dependencies": {
                "a": {"version": "1.0.0", "integrity": "sha512-x", "dependencies": {"b": {"version": "2.0.0"}}}}}))
            entries = offline.npm_entries(t / "package-lock.json")
        self.assertEqual(sorted(entries), [("a", "1.0.0", "sha512-x"), ("b", "2.0.0", None)])

    def test_fetch_fills_the_cache_without_install_scripts(self):
        seen = {}

        def run(cmd, **kw):
            seen["cmd"] = cmd
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with tree() as t:
            ok, msg = offline.fetch_npm(t, run=run)
            self.assertTrue((t / "offline-packages/npm-cache").is_dir())
        self.assertTrue(ok)
        self.assertIn("--ignore-scripts", seen["cmd"])
        bad = offline.fetch_npm(t, run=lambda c, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="offline"))
        self.assertEqual(bad, (False, "offline"))


class Command(unittest.TestCase):
    def test_usage_and_failures_are_exit_codes(self):
        with tree() as t:
            write_config(t)
            code, out = cli(t, "deps")
            self.assertEqual(code, 2)
            self.assertIn("deps lock", out[0])
            code, out = cli(t, "deps", "lock", "in=missing.in")
            self.assertEqual(code, 2)
            self.assertTrue(out[0].startswith("deps: COULD NOT RUN"), out)
