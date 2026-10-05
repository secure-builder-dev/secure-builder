# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The running application probed from outside (a dynamic scan, offline, standard library only).

The project's server is started from config serve_command (a list; "{port}" is replaced with a free local port and
PORT is set) and probed on 127.0.0.1: one idle connection must not stall the next client (the CWE-400 defect static
analysis missed in both demo apps), malformed and oversized requests must not leak a stack trace or kill the process,
routes the project declares protected must refuse an anonymous request, a Node-RED admin API must refuse one, and HTML
must carry the headers that stop content sniffing and script injection. A project with server code and no
serve_command cannot be probed, and that fails the scan rather than passing it.
"""
import os
import re
import subprocess
import time

from ..net import LOOPBACK_ERRORS, free_loopback_port as free_port, loopback_connection, loopback_request as _request

# a server module named anywhere in an import line (a mid-line `import sys; import http.server as hs` hid a server)
SERVER_CODE = [
    (re.compile(r"^[ \t]*(?:from|import)\b[^\n]*\b(http\.server|socketserver|wsgiref\.simple_server|fastapi|flask|aiohttp|"
                r"starlette|bottle|tornado|sanic|falcon|uvicorn|hypercorn|waitress|cherrypy)\b", re.M), (".py",)),
    (re.compile(r"require\(\s*['\"](node:)?(http|https|express|fastify|koa|@hapi/hapi|hapi|restify|http2)['\"]\s*\)|"
                r"from\s+['\"](node:)?(http|https|express|fastify|koa|http2)['\"]"), (".js", ".mjs", ".cjs")),
]
LEAK = re.compile(r"Traceback \(most recent call last\)|File \".*\", line \d+|\n\s+at [\w.<>]+ \(.*:\d+:\d+\)|"
                  r"node_modules[\\/]|Werkzeug Debugger|SyntaxError: Unexpected token", re.S)
BIG_BODY = 5 * 1024 * 1024


def is_server(files, flows):
    """True when the project's own code serves HTTP (or is a Node-RED project, which always does)."""
    if flows:
        return True
    for f in files:
        for pattern, suffixes in SERVER_CODE:
            if f.suffix.lower() in suffixes:
                try:
                    if pattern.search(f.read_text(encoding="utf-8", errors="replace")):
                        return True
                except OSError:
                    continue
    return False


def wait_ready(port, proc, path="/", timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if proc.poll() is not None:
            return False
        try:
            _request(port, "GET", path, timeout=2)
            return True
        except LOOPBACK_ERRORS:
            time.sleep(0.3)
    return False


def probe(root, serve_command, protected=(), node_red=False, ready_path="/", start_timeout=40):
    """(problems, findings): findings are (rule, severity, where, message)."""
    port = free_port()
    cmd = [str(a).replace("{port}", str(port)) for a in serve_command]
    env = dict(os.environ, PORT=str(port), HOST="127.0.0.1", NODE_ENV="production")
    try:
        proc = subprocess.Popen(cmd, cwd=str(root), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except OSError as e:
        return [f"dast: serve_command could not start ({e})"], []
    findings, problems = [], []
    try:
        if not wait_ready(port, proc, ready_path, start_timeout):
            err = proc.stderr.read(400).decode("utf-8", "replace") if proc.poll() is not None else ""
            return [f"dast: the server did not answer on 127.0.0.1:{port}{ready_path} within {start_timeout}s"
                    + (f" (exited: {err.strip()[:160]})" if err else "") + " — it cannot be probed, the scan fails"], []
        # one idle connection must not stall the next client
        idle = loopback_connection(port)
        try:
            t0 = time.monotonic()
            try:
                _request(port, "GET", ready_path, timeout=3)
            except LOOPBACK_ERRORS:
                findings.append(("dast-idle-connection-blocks", "HIGH", f"GET {ready_path}",
                                 "With one client connected and silent, a second request got no answer in 3 s: a single idle "
                                 "connection stalls the server (CWE-400). Serve connections concurrently and time them out."))
            else:
                if time.monotonic() - t0 > 2.5:
                    findings.append(("dast-idle-connection-slows", "MEDIUM", f"GET {ready_path}",
                                     "A second request waited on an idle connection (CWE-400)."))
        finally:
            idle.close()
        # headers on the page a person loads
        try:
            status, headers, body = _request(port, "GET", ready_path)
            if "text/html" in headers.get("content-type", ""):
                if "content-security-policy" not in headers:
                    findings.append(("dast-no-content-security-policy", "MEDIUM", f"GET {ready_path}",
                                     "HTML is served with no Content-Security-Policy: nothing limits injected script."))
                if headers.get("x-content-type-options", "").lower() != "nosniff":
                    findings.append(("dast-no-nosniff", "MEDIUM", f"GET {ready_path}",
                                     "HTML is served without X-Content-Type-Options: nosniff."))
        except LOOPBACK_ERRORS as e:
            problems.append(f"dast: GET {ready_path} failed after the idle-connection probe ({e})")
        # malformed and hostile input must not leak internals
        for method, path, body, hdrs in (("GET", "/%ff%fe%00..%2f..%2fetc%2fpasswd", None, {}),
                                         ("POST", ready_path, b"{\"broken\": ", {"Content-Type": "application/json"}),
                                         ("GET", "/" + "A" * 8000, None, {}),
                                         ("PUT", ready_path + "?x=%00%ff", b"\xff\xfe\x00", {"Content-Type": "text/plain"})):
            try:
                status, headers, text = _request(port, method, path, body, hdrs)
            except LOOPBACK_ERRORS:
                continue
            if LEAK.search(text):
                findings.append(("dast-stack-trace-leak", "HIGH", f"{method} {path[:60]}",
                                 f"A malformed request got a {status} whose body shows a stack trace or internal paths: "
                                 "errors must answer with a generic message and log the detail."))
                break
            if status >= 500 and status != 503:
                findings.append(("dast-server-error-on-malformed-input", "MEDIUM", f"{method} {path[:60]}",
                                 f"A malformed request was answered {status}: input is not validated before use."))
        # an oversized body must be refused, not crash the process
        try:
            _request(port, "POST", ready_path, b"x" * BIG_BODY, {"Content-Type": "application/octet-stream"}, timeout=10)
        except LOOPBACK_ERRORS:
            pass
        time.sleep(0.3)
        if proc.poll() is not None:
            findings.append(("dast-crash-on-large-body", "HIGH", f"POST {ready_path}",
                             f"A {BIG_BODY // (1024 * 1024)} MB request body killed the server process."))
            return problems, findings
        # routes the project declares protected refuse an anonymous caller
        for route in protected:
            for method in ("GET", "POST"):
                try:
                    status, _, _ = _request(port, method, route, b"{}" if method == "POST" else None,
                                            {"Content-Type": "application/json"} if method == "POST" else {})
                except LOOPBACK_ERRORS:
                    continue
                if 200 <= status < 300:
                    findings.append(("dast-protected-route-open", "HIGH", f"{method} {route}",
                                     f"A route declared protected answered {status} to a request with no credentials."))
        if node_red:
            for admin in ("/flows", "/settings", "/nodes"):
                try:
                    status, _, _ = _request(port, "GET", admin, headers={"Accept": "application/json"})
                except LOOPBACK_ERRORS:
                    continue
                if 200 <= status < 300:
                    findings.append(("dast-node-red-admin-open", "HIGH", f"GET {admin}",
                                     "Node-RED's admin API answered an anonymous request: anyone on the network can read and "
                                     "deploy flows. Set adminAuth, or httpAdminRoot: false."))
                    break
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    return problems, findings
