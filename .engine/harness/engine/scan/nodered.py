# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Node-RED projects: the code inside flows, and the settings that decide who can change them.

A function node's JavaScript lives as a string inside the flow file, where no analyzer looks; it is extracted to
real files so both analyzers read it, and each finding is reported against the flow and node it came from. The
settings checks are the ones Node-RED's defaults fail: an editor anyone on the network can deploy code from, HTTP
endpoints with no authentication, and credentials stored unencrypted or under a key written into the source.
"""
import json
import pathlib
import re

SETTINGS_KEYS = re.compile(r"\b(uiPort|flowFile|adminAuth|httpAdminRoot|credentialSecret|httpNodeRoot|functionGlobalContext)\s*:")
MAX_FLOW_BYTES = 8_000_000


def strip_js_comments(text):
    """Comments removed, strings kept: a commented-out `adminAuth` is not a configured one."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end < 0 else end
        else:
            out.append(c)
            i += 1
    return "".join(out)


def load_flow(path):
    """The node list of a Node-RED flow file, or None when the file is something else."""
    try:
        if path.stat().st_size > MAX_FLOW_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("flows"), list):
        data = data["flows"]
    if not isinstance(data, list) or not data or not all(isinstance(n, dict) for n in data):
        return None
    shaped = [n for n in data if "id" in n and "type" in n]
    if len(shaped) < len(data) or not any(n["type"] == "tab" or "wires" in n or "z" in n for n in shaped):
        return None
    return shaped


def find_projects(root, own_files):
    """(flow files with their nodes, settings files) among the project's own files."""
    flows, settings = [], []
    for f in own_files:
        if f.suffix.lower() == ".json" and not f.name.endswith("_cred.json"):
            nodes = load_flow(f)
            if nodes is not None:
                flows.append((f, nodes))
        elif f.suffix.lower() in (".js", ".cjs") and f.name.startswith("settings"):
            text = strip_js_comments(f.read_text(encoding="utf-8", errors="replace"))
            if "module.exports" in text and SETTINGS_KEYS.search(text):
                settings.append((f, text))
    return flows, settings


def label(node):
    name = str(node.get("name") or "").strip()
    return f"{node['type']} node '{name}' ({node['id']})" if name else f"{node['type']} node {node['id']}"


def extract_code(root, flows, outdir):
    """Write each function node's code to a file analyzers read; returns {written path relative to root: where it came from}."""
    outdir.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for f, nodes in flows:
        rel = f.relative_to(root).as_posix()
        for node in nodes:
            if node.get("type") != "function":
                continue
            parts = [(k, node.get(k)) for k in ("initialize", "func", "finalize") if isinstance(node.get(k), str) and node.get(k).strip()]
            if not parts:
                continue
            safe = re.sub(r"[^A-Za-z0-9_]", "_", str(node["id"]))
            body = "\n".join(f"async function {k}_{safe}(msg, node, context, flow, global, env, RED) {{\n{code}\n}}" for k, code in parts)
            out = outdir / f"{re.sub(r'[^A-Za-z0-9_]', '_', rel)}__{safe}.js"
            out.write_text("'use strict';\n" + body + "\n", encoding="utf-8", newline="\n")
            mapping[out.relative_to(root).as_posix()] = f"{rel}#{label(node)}"
    return mapping


def _has(text, pattern):
    return re.search(pattern, text) is not None


def findings(root, flows, settings, cred_files):
    """(rule, severity, where, message) for each Node-RED setting or node its defaults get wrong."""
    out = []
    if not flows and not settings:
        return out
    text = settings[0][1] if settings else ""
    where = settings[0][0].relative_to(root).as_posix() if settings else (flows[0][0].relative_to(root).as_posix() if flows else "settings.js")
    editor_off = _has(text, r"\bhttpAdminRoot\s*:\s*false\b")
    if not settings:
        out.append(("node-red-no-settings", "HIGH", where,
                    "Node-RED flows with no settings.js beside them: the runtime starts with its defaults, an editor with no "
                    "login that anyone on the network can deploy code from. Add settings.js with adminAuth, or httpAdminRoot: false."))
    elif not editor_off and not _has(text, r"\badminAuth\s*:\s*\{"):
        out.append(("node-red-editor-without-login", "HIGH", where,
                    "The Node-RED editor has no login (adminAuth unset): anyone who reaches it can deploy code. Set adminAuth, or "
                    "httpAdminRoot: false where the editor is not needed (a fielded system)."))
    all_nodes = [(f, n) for f, nodes in flows for n in nodes]
    http_in = [(f, n) for f, n in all_nodes if n.get("type") == "http in"]
    if http_in and not (_has(text, r"\bhttpNodeAuth\s*:\s*\{") or _has(text, r"\bhttpNodeMiddleware\s*:")):
        f, n = http_in[0]
        out.append(("node-red-http-endpoint-without-auth", "HIGH", f"{f.relative_to(root).as_posix()}#{label(n)}",
                    f"{len(http_in)} HTTP endpoint(s) served with no authentication (httpNodeAuth or httpNodeMiddleware unset)."))
    has_creds = bool(cred_files) or any(isinstance(n.get("credentials"), dict) and n["credentials"] for _, n in all_nodes)
    secret = re.search(r"\bcredentialSecret\s*:\s*([^,\n}]+)", text)
    if secret and re.match(r"\s*[\"'`]", secret.group(1)):
        out.append(("node-red-hardcoded-credential-secret", "HIGH", where,
                    "credentialSecret is written into settings.js: the key that decrypts flows_cred.json ships beside it. "
                    "Read it from the environment (process.env)."))
    elif has_creds and (not secret or re.match(r"\s*false\b", secret.group(1))):
        out.append(("node-red-credentials-unencrypted", "HIGH", where,
                    "Flows carry credentials but no credentialSecret is set (or it is false): flows_cred.json is stored "
                    "unencrypted or under a machine-generated key. Set credentialSecret from the environment."))
    for f, n in all_nodes:
        loc = f"{f.relative_to(root).as_posix()}#{label(n)}"
        if n.get("type") == "exec":
            out.append(("node-red-exec-node", "MEDIUM", loc,
                        "An exec node runs operating-system commands; if any part of the command comes from a message it is "
                        "command injection. Justify it or replace it."))
        if n.get("type") == "template" and "{{{" in str(n.get("template", "")):
            out.append(("node-red-unescaped-template", "MEDIUM", loc,
                        "A template node renders {{{ }}} without HTML escaping: cross-site scripting if the value is data."))
    if not editor_off and settings and not _has(text, r"\beditable\s*:\s*false\b"):
        out.append(("node-red-palette-editable", "MEDIUM", where,
                    "The palette manager can install nodes from npm at runtime: unreviewed code and a network dependency. "
                    "Set editorTheme.palette.editable: false."))
    if _has(text, r"\bfunctionExternalModules\s*:\s*true\b"):
        out.append(("node-red-function-external-modules", "MEDIUM", where,
                    "functionExternalModules lets function nodes install npm modules at runtime: unreviewed code outside the "
                    "lockfile the scanners read."))
    return out
