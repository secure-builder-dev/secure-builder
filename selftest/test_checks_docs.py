# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Reference integrity, document consistency, attack surface, license policy, lint (spec 01 §10)."""
import json
import unittest

from engine import distribute, licenses
from engine.checks import attack_surface, doc_consistency, license_policy, lint, reference_integrity
from engine.config import Config
from engine.outcome import State
from .helpers import cli, find_line, git, git_repo, tree, write, write_config
from .stubs import stub_path, stub_tool


def cfg(**over):
    d = {"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local"}
    d.update(over)
    return Config(d)


class ReferenceIntegrity(unittest.TestCase):
    def test_unresolved_citation_is_blocking(self):
        with tree() as t:
            write(t, "AGENTS.md", "See `docs/missing.md` and `src/app.py`." + chr(10))
            write(t, "src/app.py", "")
            o = reference_integrity.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["AGENTS.md: `docs/missing.md` does not resolve"])

    def test_all_resolve(self):
        with tree() as t:
            write(t, "AGENTS.md", "See `src/app.py`." + chr(10))
            write(t, "src/app.py", "")
            o = reference_integrity.run(t, cfg())
            self.assertEqual(o.line(), "[reference-integrity] CLEAN: 1 cited paths in 1 governed documents all resolve")

    def test_empty_governed_set_is_not_a_pass(self):
        with tree() as t:
            o = reference_integrity.run(t, cfg())
            self.assertIs(o.state, State.COULD_NOT_RUN)
            self.assertIn("nothing to check is not a pass", o.detail)

    def test_governed_set_is_explicit_not_inferred(self):
        with tree() as t:
            write(t, "AGENTS.md", "See `nope/x.md`." + chr(10))
            write(t, "docs/other.md", "See `also/missing.md`." + chr(10))
            o = reference_integrity.run(t, cfg(governed_documents=["docs/other.md"]))
            self.assertEqual(o.findings, ["docs/other.md: `also/missing.md` does not resolve"])

    def test_prose_that_resembles_a_path_is_not_misread(self):
        self.assertEqual(reference_integrity.citations("see `https://example.invalid/x` and `1.2` and `C:/tmp/x`"), [])

    def test_doc_relative_citation_resolves(self):
        with tree() as t:
            write(t, "hooks/README.md", "Run `install.py`." + chr(10))
            write(t, "hooks/install.py", "")
            o = reference_integrity.run(t, cfg(governed_documents=["hooks/README.md"]))
            self.assertIs(o.state, State.CLEAN)

    def test_placed_templates_cite_only_paths_that_exist_in_a_project(self):
        with tree() as t:
            write_config(t)
            distribute.update(t)
            o = reference_integrity.run(t, cfg())
            self.assertIs(o.state, State.CLEAN, o.lines())


class DocConsistency(unittest.TestCase):
    BLOCK = "<!-- engine:block verdict -->" + chr(10) + "| pass | tier |" + chr(10) + "<!-- engine:end verdict -->"

    def test_declared_block_with_disagreeing_copies_is_blocking(self):
        with tree() as t:
            write(t, "AGENTS.md", "Read and follow: .engine/rules/RULES.md" + chr(10) + self.BLOCK + chr(10))
            write(t, ".engine/rules/RULES.md", self.BLOCK.replace("| pass | tier |", "| pass |") + chr(10))
            o = doc_consistency.run(t, cfg(consistency_blocks=["verdict"]))
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["block 'verdict': 2 copies disagree (AGENTS.md, .engine/rules/RULES.md)"])

    def test_identical_copies_are_clean(self):
        with tree() as t:
            write(t, "AGENTS.md", "Read and follow: .engine/rules/RULES.md" + chr(10) + self.BLOCK + chr(10))
            write(t, ".engine/rules/RULES.md", self.BLOCK + chr(10))
            o = doc_consistency.run(t, cfg(consistency_blocks=["verdict"]))
            self.assertIs(o.state, State.CLEAN)

    def test_declared_block_found_nowhere_fails_rather_than_passing(self):
        with tree() as t:
            write(t, "AGENTS.md", "nothing here" + chr(10))
            o = doc_consistency.run(t, cfg(consistency_blocks=["verdict"]))
            self.assertIs(o.state, State.FINDINGS)
            self.assertEqual(o.findings, ["block 'verdict': expected in at least two documents, found in 0 (nowhere) — nothing to compare"])

    def test_declared_block_found_once_fails(self):
        with tree() as t:
            write(t, "AGENTS.md", self.BLOCK + chr(10))
            o = doc_consistency.run(t, cfg(consistency_blocks=["verdict"]))
            self.assertEqual(o.findings, ["block 'verdict': expected in at least two documents, found in 1 (AGENTS.md) — nothing to compare"])

    def test_follows_reference_chain_into_included_file(self):
        with tree() as t:
            write(t, "AGENTS.md", "Read and follow: docs/inc.md" + chr(10) + self.BLOCK + chr(10))
            write(t, "docs/inc.md", self.BLOCK + chr(10))
            o = doc_consistency.run(t, cfg(consistency_blocks=["verdict"]))
            self.assertIs(o.state, State.CLEAN, o.lines())

    def test_nothing_declared_is_nothing_yet(self):
        with tree() as t:
            self.assertIs(doc_consistency.run(t, cfg()).state, State.NOTHING_YET)


class AttackSurface(unittest.TestCase):
    def test_new_risky_directive_is_blocking(self):
        with tree() as t:
            write(t, "nginx.conf", "server {" + chr(10) + "  autoindex on;" + chr(10) + "}" + chr(10))
            o = attack_surface.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(len(o.findings), 1)
            self.assertTrue(o.findings[0].startswith("nginx.conf:2: autoindex on; [directory listing]"), o.findings)

    def test_accepted_directive_is_clean(self):
        with tree() as t:
            write(t, "nginx.conf", "autoindex on;" + chr(10))
            attack_surface.accept(t, "nginx.conf:directory listing", "static file share by design", "casey")
            o = attack_surface.run(t, cfg())
            self.assertIs(o.state, State.CLEAN)
            self.assertIn("1 risky directive(s), all previously accepted", o.detail)

    def test_accept_command_records_reason_and_person(self):
        with tree() as t:
            write(t, "docker-compose.yml", "privileged: true" + chr(10))
            code, lines = cli(t, "accept-directive", "docker-compose.yml:privileged container", "needs device access", "casey")
            self.assertEqual(code, 0)
            data = json.loads((t / attack_surface.BASELINE).read_text())
            self.assertEqual(data["accepted"]["docker-compose.yml:privileged container"], {"reason": "needs device access", "by": "casey"})
            self.assertIs(attack_surface.run(t, cfg()).state, State.CLEAN)

    def test_no_config_surface_is_nothing_yet(self):
        with tree() as t:
            write(t, "src/app.py", "")
            self.assertIs(attack_surface.run(t, cfg()).state, State.NOTHING_YET)

    def test_directive_catalogue(self):
        with tree() as t:
            write(t, "deploy.yaml", "hostNetwork: true" + chr(10) + "allowPrivilegeEscalation: true" + chr(10) + "runAsUser: 0" + chr(10))
            found = attack_surface.directives_in(t)
            self.assertEqual(set(k.split(":", 1)[1] for k in found), {"host network", "privilege escalation", "root user"})


class LicensePolicy(unittest.TestCase):
    LOCK = json.dumps({"packages": {"": {}, "node_modules/left": {"version": "1.0.0", "license": "MIT"},
                                    "node_modules/gpl-thing": {"version": "2.0.0", "license": "GPL-3.0"},
                                    "node_modules/mystery": {"version": "0.1.0"}}})

    def test_record_generated_by_tooling(self):
        with tree() as t:
            write(t, "package-lock.json", self.LOCK)
            rows = licenses.write_record(t)
            self.assertEqual(rows, [("gpl-thing", "2.0.0", "GPL-3.0", "package-lock.json"),
                                    ("left", "1.0.0", "MIT", "package-lock.json"),
                                    ("mystery", "0.1.0", "UNKNOWN", "package-lock.json")])
            self.assertTrue((t / licenses.RECORD).read_text().startswith("# generated by the harness"))

    def test_outside_policy_is_blocking(self):
        with tree() as t:
            write(t, "package-lock.json", self.LOCK)
            write(t, licenses.POLICY, json.dumps({"allowed": ["MIT", "Apache-2.0"], "denied": ["GPL-3.0"]}))
            o = license_policy.run(t, cfg())
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertEqual(o.findings, ["gpl-thing@2.0.0: license GPL-3.0 is denied by policy (package-lock.json)",
                                          "mystery@0.1.0: license UNKNOWN (package-lock.json) — cannot be shown to satisfy the policy"])

    def test_within_policy_is_clean(self):
        with tree() as t:
            write(t, "package-lock.json", json.dumps({"packages": {"node_modules/a": {"version": "1", "license": "MIT"}}}))
            write(t, licenses.POLICY, json.dumps({"allowed": ["MIT"]}))
            self.assertIs(license_policy.run(t, cfg()).state, State.CLEAN)

    def test_no_policy_cannot_evaluate(self):
        with tree() as t:
            write(t, "package-lock.json", self.LOCK)
            o = license_policy.run(t, cfg())
            self.assertIs(o.state, State.COULD_NOT_RUN)
            self.assertIn("no license policy is declared", o.detail)

    def test_no_components_is_nothing_yet(self):
        with tree() as t:
            self.assertIs(license_policy.run(t, cfg()).state, State.NOTHING_YET)
            self.assertIn("no third-party components", (t / licenses.RECORD).read_text())


class Lint(unittest.TestCase):
    def test_failing_lint_is_blocking(self):
        with tree() as t:
            stub_tool(t / "bin", "linter", exit_code=1, stdout="src/x.py:1: unused import" + chr(10))
            import os
            old = os.environ.get("PATH", "")
            os.environ["PATH"] = stub_path(t / "bin")
            try:
                o = lint.run(t, cfg(lint_command=["linter", "src"]))
            finally:
                os.environ["PATH"] = old
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertTrue(o.findings[0].startswith("lint failed (exit 1): src/x.py:1: unused import"), o.findings)

    def test_missing_tool_could_not_run(self):
        with tree() as t:
            o = lint.run(t, cfg(lint_command=["no-such-linter-xyz", "."]))
            self.assertIs(o.state, State.COULD_NOT_RUN)

    def test_no_configuration_is_nothing_yet(self):
        with tree() as t:
            self.assertIs(lint.run(t, cfg()).state, State.NOTHING_YET)

    def test_track_manifest_supplies_command(self):
        with tree() as t:
            write(t, "package.json", json.dumps({"scripts": {"lint": "eslint ."}}))
            self.assertEqual(lint.commands_for(t, cfg()), [("lint", ["npm", "run", "lint", "--silent"])])
