# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Control manifest, wiring verification and mutation (spec 01 §7, §5.3)."""
import json
import unittest

from engine import controlshape, manifest, mutate
from engine.checks import control_manifest
from engine.config import Config
from engine.outcome import State
from engine.records import table, templates
from .helpers import cli, commit, find_line, git, git_repo, tree, write, write_config

CFG = Config({"schema": 1, "track": "web", "tier": "IL4", "provider": "aws", "app_type": "n/a", "mode": "local", "side": "low"})
NL = chr(10)

AUTH_PY = ("def require_auth(request, next):" + NL +
           '    """Reject requests without a valid token."""' + NL +
           "    if not request.get('token'):" + NL +
           "        raise PermissionError('no token')" + NL +
           "    return next(request)" + NL + NL +
           "def can_delete(user, record):" + NL +
           "    return user['id'] == record['owner']" + NL + NL +
           "def scope_to_owner(query, user):" + NL +
           "    return [r for r in query if r['owner'] == user['id']]" + NL)
APP_PY = ("from auth import require_auth, can_delete, scope_to_owner" + NL +
          "ROUTES = [('GET', '/x', require_auth)]   # registered by reference" + NL +
          "def delete(user, record):" + NL +
          "    # can_delete is mentioned in this comment only" + NL +
          "    if not can_delete(user, record):" + NL +
          "        raise PermissionError" + NL +
          "def listing(user, rows):" + NL +
          "    return scope_to_owner(rows, user)" + NL)
TEST_PY = "from auth import require_auth" + NL + "def test_auth(): assert require_auth" + NL


def control(id, symbol, file="src/auth.py", test="tests/test_auth*", status="system-specific", **extra):
    c = {"id": id, "description": f"{symbol} control", "location": {"file": file, "symbol": symbol},
         "required_artifact": None, "test_pattern": test, "status": status, "counterpart": None, "mutation": None}
    c.update(extra)
    return c


def manifest_with(t, controls):
    write(t, manifest.FILE, json.dumps({"schema": 1, "scope_statement": manifest.SCOPE_STATEMENT, "controls": controls}))


def project(t):
    git_repo(t)
    write(t, "src/auth.py", AUTH_PY)
    write(t, "src/app.py", APP_PY)
    write(t, "tests/test_auth.py", TEST_PY)
    git(t, "add", "-A")
    return t


class Structure(unittest.TestCase):
    def test_scope_statement_required_verbatim(self):
        data = {"scope_statement": "covers some controls", "controls": []}
        self.assertIn("scope statement is missing or differs from the required text", manifest.problems(data))
        self.assertEqual(manifest.problems({"scope_statement": manifest.SCOPE_STATEMENT, "controls": []}), [])

    def test_inherited_controls_not_present(self):
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [control("C-1", "x", status="inherited")]}
        self.assertIn("C-1: inherited controls are not present in the manifest; they are covered by the scope statement",
                      manifest.problems(data))

    def test_hybrid_requires_counterpart(self):
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [control("C-1", "x", status="hybrid")]}
        self.assertIn("C-1: a hybrid control names its shared-responsibility counterpart", manifest.problems(data))
        data["controls"][0]["counterpart"] = "platform ingress gateway terminates TLS"
        self.assertEqual(manifest.problems(data), [])

    def test_stored_call_sites_rejected(self):
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [control("C-1", "x", call_sites=["a.py:3"])]}
        self.assertIn("C-1: call sites are recomputed on every run, never stored ('call_sites')", manifest.problems(data))

    def test_multi_branch_single_mutation_needs_rationale(self):
        c = control("C-1", "x", branches=[{"name": "create", "edits": []}, {"name": "update", "edits": []}],
                    mutation={"shape": "decision"})
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [c]}
        self.assertIn("C-1: a single mutation for a multi-branch control must state why it is representative", manifest.problems(data))
        c["mutation"]["rationale"] = "both branches share one guard"
        self.assertEqual(manifest.problems(data), [])

    def test_template_is_template_only(self):
        with tree() as t:
            import pathlib, shutil
            (t / ".engine").mkdir()
            shutil.copy(pathlib.Path(__file__).resolve().parent.parent / "engine/dist/templates/control-manifest.json", t / manifest.FILE)
            state, results, structural = manifest.verify(t)
            self.assertEqual((state, results, structural), ("template-only", [], []))


class Recomputation(unittest.TestCase):
    def test_call_sites_recomputed_direct_indirect_not_comment_not_test(self):
        with tree() as t:
            project(t)
            self.assertEqual(manifest.call_sites(t, "require_auth", "src/auth.py"), ["src/app.py:2"])
            self.assertEqual(manifest.call_sites(t, "can_delete", "src/auth.py"), ["src/app.py:5"])
            self.assertEqual(manifest.call_sites(t, "scope_to_owner", "src/auth.py"), ["src/app.py:8"])

    def test_definition_line_excluded(self):
        with tree() as t:
            project(t)
            write(t, "src/app.py", "x = 1" + NL)
            git(t, "add", "-A")
            self.assertEqual(manifest.call_sites(t, "require_auth", "src/auth.py"), [])

    def test_python_decorator_counts_as_indirect_invocation(self):
        with tree() as t:
            project(t)
            write(t, "src/app.py", "from auth import require_auth" + NL + "@require_auth" + NL + "def view(): pass" + NL)
            git(t, "add", "-A")
            self.assertEqual(manifest.call_sites(t, "require_auth", "src/auth.py"), ["src/app.py:2"])


class Verify(unittest.TestCase):
    def test_all_resolve(self):
        with tree() as t:
            project(t)
            manifest_with(t, [control("C-1", "require_auth"), control("C-2", "can_delete"), control("C-3", "scope_to_owner")])
            state, results, _ = manifest.verify(t)
            self.assertEqual(state, "resolved")
            self.assertEqual([r["problems"] for r in results], [[], [], []])
            o = control_manifest.run(t, CFG)
            self.assertIs(o.state, State.CLEAN)
            self.assertEqual(o.line(), "[control-manifest] CLEAN: 3 declared control(s) implemented, called from production code, tested")

    def test_lost_call_site_fails(self):
        with tree() as t:
            project(t)
            manifest_with(t, [control("C-1", "require_auth")])
            write(t, "src/app.py", "from auth import require_auth" + NL + "# require_auth no longer registered" + NL)
            git(t, "add", "-A")
            state, results, _ = manifest.verify(t)
            self.assertEqual(state, "failed")
            self.assertEqual(results[0]["problems"], ["require_auth has no production call site (recomputed; definition and tests excluded)"])
            o = control_manifest.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)

    def test_missing_symbol_artifact_and_test_reported(self):
        with tree() as t:
            project(t)
            manifest_with(t, [control("C-1", "require_auth", required_artifact="infra/policy.json", test="tests/test_nope*")])
            state, results, _ = manifest.verify(t)
            self.assertEqual(state, "failed")
            self.assertEqual(results[0]["problems"], ["required artifact infra/policy.json is absent", "no test matches tests/test_nope*"])
            manifest_with(t, [control("C-1", "ghost_symbol")])
            state, results, _ = manifest.verify(t)
            self.assertIn("symbol ghost_symbol is not defined in src/auth.py", results[0]["problems"])

    def test_invalid_manifest_is_blocking(self):
        with tree() as t:
            project(t)
            write(t, manifest.FILE, json.dumps({"scope_statement": "x", "controls": [{"id": "C-1"}]}))
            o = control_manifest.run(t, CFG)
            self.assertIs(o.state, State.FINDINGS)
            self.assertTrue(o.blocking)
            self.assertIn("scope statement is missing or differs from the required text", o.findings)

    def test_absent_manifest_could_not_run(self):
        with tree() as t:
            self.assertIs(control_manifest.run(t, CFG).state, State.COULD_NOT_RUN)

    def test_manifest_command(self):
        with tree() as t:
            project(t)
            manifest_with(t, [control("C-1", "require_auth")])
            code, lines = cli(t, "manifest")
            self.assertEqual(code, 0, lines)
            find_line(lines, "manifest: resolved")
            find_line(lines, "      called at src/app.py:2")


class Shapes(unittest.TestCase):
    def test_shape_inference(self):
        self.assertEqual(mutate.infer_shape("require_auth", "def require_auth(request, next):"), "middleware")
        self.assertEqual(mutate.infer_shape("can_delete", "def can_delete(user, record):"), "decision")
        self.assertEqual(mutate.infer_shape("scope_to_owner", "def scope_to_owner(query, user):"), "scoping")
        self.assertEqual(mutate.infer_shape("redact_pii", "def redact_pii(obj):"), "redaction")
        self.assertEqual(mutate.infer_shape("rotate_keys", "def rotate_keys():"), "other")

    def test_mutations_by_shape_python(self):
        mutated, desc = mutate.mutate_source(AUTH_PY, "require_auth")
        self.assertEqual(mutated.splitlines()[2], "    return next(request)  # engine:mutation")
        self.assertTrue(desc.startswith("middleware:"))
        mutated, _ = mutate.mutate_source(AUTH_PY, "can_delete")
        self.assertEqual(mutated.splitlines()[6:8], ["def can_delete(user, record):", "    return True  # engine:mutation"])
        mutated, _ = mutate.mutate_source(AUTH_PY, "scope_to_owner")
        self.assertEqual(mutated.splitlines()[9:11], ["def scope_to_owner(query, user):", "    return query  # engine:mutation"])

    def test_mutation_javascript(self):
        src = "export function canEdit(user, doc) {" + NL + "  return user.id === doc.owner;" + NL + "}" + NL
        text, desc = mutate.mutate_source(src, "canEdit")
        self.assertTrue(text.startswith("export function canEdit(user, doc) { return true; /* engine:mutation */"), text)

    def test_unsupported_language_needs_override(self):
        text, reason = mutate.mutate_source("fun canEdit(u: User): Boolean = true", "canEdit")
        self.assertIsNone(text)
        self.assertIn("declare an explicit mutation override", reason)


class Mutation(unittest.TestCase):
    def suite_that_checks(self, t):
        """A stub suite: exit 1 when any control is mutated (it notices), else 0."""
        def runner():
            src = (t / "src/auth.py").read_text(encoding="utf-8")
            return 1 if "engine:mutation" in src or "mutated" in src else 0
        return runner

    def test_every_control_mutated_suite_must_fail_and_files_restored(self):
        with tree() as t:
            project(t); write_config(t)
            templates.render_all(t / ".engine/records")
            controls = [control("C-1", "require_auth"), control("C-2", "can_delete")]
            original = (t / "src/auth.py").read_bytes()
            summary = mutate.run(t, CFG, controls, test_command=["x"], runner=self.suite_that_checks(t))
            self.assertEqual(summary["state"], "passed")
            self.assertEqual([r["verdict"] for r in summary["results"]], ["suite-failed", "suite-failed"])
            self.assertEqual((t / "src/auth.py").read_bytes(), original, "mutated file must be restored byte for byte")
            rows, _ = mutate.read_results(t)
            self.assertEqual([r["control"] for r in rows], ["C-1", "C-2"])
            self.assertEqual(rows[0]["result"], "suite-failed")

    def test_control_whose_mutation_leaves_suite_green_is_a_finding(self):
        with tree() as t:
            project(t); write_config(t)
            templates.render_all(t / ".engine/records")
            summary = mutate.run(t, CFG, [control("C-1", "require_auth")], test_command=["x"], runner=lambda: 0)
            self.assertEqual(summary["state"], "failed")
            self.assertEqual(summary["results"][0]["verdict"], "suite-stayed-green")

    def test_red_baseline_aborts(self):
        with tree() as t:
            project(t); write_config(t)
            calls = []
            def runner():
                calls.append(1)
                return 1
            summary = mutate.run(t, CFG, [control("C-1", "require_auth")], test_command=["x"], runner=runner)
            self.assertEqual(summary["state"], "red-baseline")
            self.assertEqual(len(calls), 1, "no mutation is attempted against a red baseline")

    def test_each_branch_mutated_independently(self):
        with tree() as t:
            project(t); write_config(t)
            templates.render_all(t / ".engine/records")
            c = control("C-2", "can_delete", branches=[
                {"name": "owner", "edits": [{"find": "user['id'] == record['owner']", "replace": "True  # mutated"}]},
                {"name": "raise", "edits": [{"find": "raise PermissionError('no token')", "replace": "pass  # mutated"}]}])
            summary = mutate.run(t, CFG, [c], test_command=["x"], runner=self.suite_that_checks(t))
            self.assertEqual([(r["branch"], r["verdict"]) for r in summary["results"]], [("owner", "suite-failed"), ("raise", "suite-failed")])

    def test_no_test_command_could_not_run(self):
        with tree() as t:
            project(t)
            summary = mutate.run(t, CFG, [control("C-1", "require_auth")])
            self.assertEqual(summary["state"], "could-not-run")


class ControlShape(unittest.TestCase):
    def test_families_detected(self):
        self.assertEqual(controlshape.families_in("def require_auth(): pass"), ["authentication", "authorization"])
        self.assertEqual(controlshape.families_in("redact_pii(record)"), ["redaction"])
        self.assertEqual(controlshape.families_in("def render_page(): pass"), [])

    def test_diff_is_control_shaped_on_added_lines_or_paths(self):
        diff = "+++ b/src/views.py" + NL + "+def show(): pass" + NL
        self.assertEqual(controlshape.diff_is_control_shaped(diff), [])
        diff = "+++ b/src/views.py" + NL + "+    if not can_edit(user): raise" + NL
        self.assertEqual(controlshape.diff_is_control_shaped(diff), ["authorization"])
        diff = "+++ b/src/auth/session.py" + NL + "+x = 1" + NL
        self.assertEqual(controlshape.diff_is_control_shaped(diff), ["authentication"])

    def test_control_symbols_in_file(self):
        syms = controlshape.control_symbols("src/auth.py", AUTH_PY)
        self.assertEqual([(s[0], s[2]) for s in syms], [("require_auth", ["authentication", "authorization"]), ("can_delete", ["authorization"]),
                                                        ("scope_to_owner", ["scoping"])])


class StructureMore(unittest.TestCase):
    def test_entry_requires_every_field(self):
        c = control("C-1", "x")
        del c["test_pattern"]
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [c]}
        self.assertIn("C-1: missing 'test_pattern'", manifest.problems(data))

    def test_status_vocabulary_is_the_assessment_one(self):
        data = {"scope_statement": manifest.SCOPE_STATEMENT, "controls": [control("C-1", "x", status="custom")]}
        self.assertIn("C-1: status must be one of ('system-specific', 'hybrid')", manifest.problems(data))

    def test_check_reports_template_only_distinctly(self):
        with tree() as t:
            import pathlib, shutil
            (t / ".engine").mkdir()
            shutil.copy(pathlib.Path(__file__).resolve().parent.parent / "engine/dist/templates/control-manifest.json", t / manifest.FILE)
            o = control_manifest.run(t, CFG)
            self.assertIs(o.state, State.NOTHING_YET)
            self.assertTrue(o.line().startswith("[control-manifest] NOTHING TO CHECK YET"), o.line())
