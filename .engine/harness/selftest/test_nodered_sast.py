# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Static analysis per language, failing closed, and Node-RED flows and settings."""
import json
import unittest

from engine.scan import nodered, runner
from .helpers import commit, git_repo, tree, write
from .test_scan import Fake, baseline, cfg

NL = chr(10)
FLOW = [{"id": "t1", "type": "tab", "label": "Flow 1"},
        {"id": "f1", "type": "function", "z": "t1", "name": "parse", "func": "const x = eval(msg.payload);" + NL + "return msg;",
         "wires": [[]]},
        {"id": "h1", "type": "http in", "z": "t1", "url": "/ingest", "method": "post", "wires": [["f1"]]},
        {"id": "e1", "type": "exec", "z": "t1", "command": "ls", "wires": [[], [], []]},
        {"id": "m1", "type": "template", "z": "t1", "template": "<p>{{{payload}}}</p>", "wires": [[]]}]
SECURE = ("module.exports = {" + NL + "  uiPort: 1880," + NL +
          "  adminAuth: { type: 'credentials', users: [] }," + NL +
          "  httpNodeAuth: { user: 'u', pass: 'h' }," + NL +
          "  credentialSecret: process.env.NODE_RED_CREDENTIAL_SECRET," + NL +
          "  editorTheme: { palette: { editable: false } }" + NL + "};" + NL)


def scan(t, script=None, **over):
    if not (t / ".git").exists():
        git_repo(t)
    commit(t, "plant")
    sc = runner.Scan(t, cfg(ship_images={}, sast_eslint_config=str(t / ".engine/eslint.config.cjs"), **over),
                     invoke=Fake(script or baseline(vulns=False)), engine=("containers", "docker"))
    return sc, sc.run()


def project(t):
    write(t, "README.md", "x" + NL)
    write(t, ".engine/eslint.config.cjs", "module.exports = [];" + NL)


class Settings(unittest.TestCase):
    def rules(self, t, flows, settings_text=None, creds=()):
        if settings_text is not None:
            write(t, "settings.js", settings_text)
        write(t, "flows.json", json.dumps(flows))
        files = [p for p in t.rglob("*") if p.is_file()]
        fl, st = nodered.find_projects(t, files)
        return sorted((r, s) for r, s, _, _ in nodered.findings(t, fl, st, list(creds)))

    def test_the_defaults_fail(self):
        with tree() as t:
            got = self.rules(t, FLOW)
        self.assertIn(("node-red-no-settings", "HIGH"), got)
        self.assertIn(("node-red-http-endpoint-without-auth", "HIGH"), got)
        self.assertIn(("node-red-exec-node", "MEDIUM"), got)
        self.assertIn(("node-red-unescaped-template", "MEDIUM"), got)

    def test_a_commented_out_admin_auth_is_not_configured(self):
        with tree() as t:
            got = self.rules(t, FLOW[:2], "module.exports = {" + NL + "  uiPort: 1880," + NL + "  // adminAuth: { type: 'credentials' }," + NL + "};" + NL)
        self.assertIn(("node-red-editor-without-login", "HIGH"), got)

    def test_secure_settings_pass_and_the_editor_can_be_switched_off(self):
        with tree() as t:
            self.assertEqual(self.rules(t, FLOW[:3], SECURE), [])
        with tree() as t:
            off = "module.exports = {" + NL + "  flowFile: 'flows.json'," + NL + "  httpAdminRoot: false," + NL + "};" + NL
            self.assertEqual(self.rules(t, FLOW[:2], off), [])

    def test_credentials_need_a_secret_from_the_environment(self):
        with tree() as t:
            write(t, "flows_cred.json", "{}")
            got = self.rules(t, FLOW[:2], SECURE.replace("  credentialSecret: process.env.NODE_RED_CREDENTIAL_SECRET," + NL, ""),
                             creds=[t / "flows_cred.json"])
        self.assertIn(("node-red-credentials-unencrypted", "HIGH"), got)
        with tree() as t:
            got = self.rules(t, FLOW[:2], SECURE.replace("process.env.NODE_RED_CREDENTIAL_SECRET", "'hunter2'"))
        self.assertIn(("node-red-hardcoded-credential-secret", "HIGH"), got)

    def test_runtime_installs_are_flagged(self):
        with tree() as t:
            got = self.rules(t, FLOW[:2], SECURE.replace("editable: false", "editable: true")
                             .replace("uiPort: 1880,", "uiPort: 1880," + NL + "  functionExternalModules: true,"))
        self.assertIn(("node-red-palette-editable", "MEDIUM"), got)
        self.assertIn(("node-red-function-external-modules", "MEDIUM"), got)

    def test_only_node_red_flow_files_are_read_as_flows(self):
        with tree() as t:
            write(t, "data.json", json.dumps([{"id": 1, "type": "point"}]))
            write(t, "package.json", json.dumps({"name": "x"}))
            write(t, "flows.json", json.dumps(FLOW))
            fl, _ = nodered.find_projects(t, [p for p in t.rglob("*") if p.is_file()])
        self.assertEqual([f.name for f, _ in fl], ["flows.json"])

    def test_function_code_is_extracted_and_named_by_its_node(self):
        with tree() as t:
            write(t, "flows.json", json.dumps(FLOW))
            fl, _ = nodered.find_projects(t, [t / "flows.json"])
            mapping = nodered.extract_code(t, fl, t / ".engine/work/flow-code")
            (path, where), = mapping.items()
            code = (t / path).read_text(encoding="utf-8")
        self.assertEqual(where, "flows.json#function node 'parse' (f1)")
        self.assertIn("async function func_f1(msg, node, context, flow, global, env, RED) {", code)
        self.assertIn("eval(msg.payload)", code)

    def test_comment_stripping_keeps_strings(self):
        self.assertEqual(nodered.strip_js_comments("a: 'http://x', // c" + NL + "/* d */ b"), "a: 'http://x', " + NL + " b")


class Languages(unittest.TestCase):
    def test_a_language_no_analyzer_reads_fails_the_scan(self):
        with tree() as t:
            project(t)
            write(t, "app/src/Main.kt", "fun main() {}" + NL)
            sc, r = scan(t)
        self.assertEqual(r["verdict"], "red")
        self.assertTrue(any("no static analyzer covers the kotlin code (1 file(s), e.g. app/src/Main.kt)" in p for p in r["problems"]),
                        r["problems"])
        self.assertNotIn("sast-b", r["ran"])

    def test_javascript_gets_eslint_and_its_findings_gate(self):
        out = json.dumps([{"filePath": "web/app.js", "messages": [
            {"ruleId": "security/detect-child-process", "severity": 1, "line": 3, "message": "child_process"},
            {"ruleId": "security/detect-non-literal-fs-filename", "severity": 1, "line": 9, "message": "fs"},
            {"ruleId": "no-unused-vars", "severity": 2, "line": 1, "message": "style"}]}])
        with tree() as t:
            project(t)
            write(t, "web/app.js", "require('child_process');" + NL)
            sc, r = scan(t, dict(baseline(vulns=False), **{"eslint --config": (1, out)}))
        self.assertIn("sast-b-javascript", r["ran"])
        self.assertIn("sast-b", r["ran"])
        self.assertEqual([(f.id, f.severity) for f in r["actionable"]], [("security-detect-child-process", "HIGH")])
        self.assertIn("security-detect-non-literal-fs-filename", [f.id for f in r["carried"]])
        args = next(a for tool, a, _ in sc.invoke.calls if tool == "eslint")
        self.assertTrue(any(a.endswith("web") for a in args), args)

    def test_eslint_without_a_rule_set_or_failing_fails_the_scan(self):
        with tree() as t:
            write(t, "web/app.js", "x" + NL)
            git_repo(t)
            commit(t, "plant")
            sc = runner.Scan(t, cfg(ship_images={}, sast_eslint_config=str(t / "nope.cjs")), invoke=Fake(baseline(vulns=False)),
                             engine=("containers", "docker"))
            r = sc.run()
        self.assertTrue(any("sast-b (eslint): no configuration" in p for p in r["problems"]))
        self.assertNotIn("sast-b", r["ran"])
        with tree() as t:
            project(t)
            write(t, "web/app.js", "x" + NL)
            sc, r = scan(t, dict(baseline(vulns=False), **{"eslint --config": (2, "boom")}))
        self.assertTrue(any("sast-b-javascript (eslint): fell over" in p for p in r["problems"]), r["problems"])

    def test_a_file_eslint_cannot_parse_is_a_problem(self):
        out = json.dumps([{"filePath": "web/app.ts.js", "messages": [{"fatal": True, "message": "Unexpected token", "line": 1}]}])
        with tree() as t:
            project(t)
            write(t, "web/app.js", "x" + NL)
            sc, r = scan(t, dict(baseline(vulns=False), **{"eslint --config": (1, out)}))
        self.assertTrue(any("could not parse web/app.ts.js" in p for p in r["problems"]), r["problems"])

    def test_flow_code_is_analyzed_and_reported_against_its_node(self):
        with tree() as t:
            project(t)
            write(t, "flows.json", json.dumps(FLOW[:2]))
            write(t, "settings.js", SECURE)
            extracted = ".engine/work/flow-code/flows_json__f1.js"
            out = json.dumps([{"filePath": str(t / extracted), "messages": [
                {"ruleId": "security/detect-eval-with-expression", "severity": 1, "line": 3, "message": "eval"}]}])
            sg = json.dumps({"results": [{"check_id": "x.eval-detected", "path": extracted, "start": {"line": 3},
                                          "extra": {"severity": "ERROR", "message": "eval", "metadata": {"category": "security"}}}],
                             "errors": []})
            sc, r = scan(t, {"--quiet /src/.engine/work/flow-code": (1, sg), **baseline(vulns=False), "eslint --config": (1, out)})
            self.assertTrue((t / extracted).is_file())
        where = {(f.id, f.package) for f in r["actionable"]}
        self.assertIn(("security-detect-eval-with-expression", "flows.json#function node 'parse' (f1)"), where)
        self.assertIn(("eval-detected", "flows.json#function node 'parse' (f1)"), where)
        args = next(a for tool, a, _ in sc.invoke.calls if tool == "eslint")
        self.assertTrue(any(a.endswith(".engine/work/flow-code") for a in args), args)

    def test_node_red_settings_findings_gate(self):
        with tree() as t:
            project(t)
            write(t, "flows.json", json.dumps(FLOW[:3]))
            sc, r = scan(t)
        self.assertEqual(r["verdict"], "red")
        self.assertIn("node-red-no-settings", [f.id for f in r["actionable"]])

    def test_a_python_project_still_gets_bandit_only(self):
        with tree() as t:
            project(t)
            write(t, "src/app.py", "x = 1" + NL)
            sc, r = scan(t)
        tools = {tool for tool, _, _ in sc.invoke.calls}
        self.assertIn("bandit", tools)
        self.assertNotIn("eslint", tools)
        self.assertIn("sast-b", r["ran"])
