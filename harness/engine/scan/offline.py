# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""A project's third-party packages, held where it can be built disconnected and verified when it is.

Every pinned Python requirement carries the hash of the file pip may install, and every npm lockfile entry its
integrity; each of those files is held in the project's offline package source (config offline_packages, default
offline-packages/): wheels and sdists for pip, npm's content-addressed cache for npm. A package that is only on a
public index is a build that fails the first time the network is gone, and an unhashed one is a file nobody checked.
`deps lock` and `deps fetch` fill the source once, while connected.
"""
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys

DEFAULT_DIR = "offline-packages"
REQ_FILE = re.compile(r"^requirements[\w.-]*\.txt$", re.I)
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*===?\s*([^\s;,\\]+)")
HASH = re.compile(r"--hash[=\s]+sha256:([0-9a-fA-F]{64})")
DIST = re.compile(r"^(?P<name>.+?)-(?P<version>\d[^-]*?)(?:-[^-]+-[^-]+-[^-]+\.whl|\.tar\.gz|\.zip)$")


def requirement_pins(path):
    """[(line, name, version, [sha256 hashes])] for each pinned requirement, continuation lines joined."""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").replace("\\\n", " ").splitlines():
        req = line.split(" #", 1)[0].strip()
        if not req or req.startswith(("#", "-")):
            continue
        m = PIN.match(req)
        if m:
            out.append((req.split(" --", 1)[0].strip(), m.group(1), m.group(2), [h.lower() for h in HASH.findall(req)]))
    return out


def _this_platform(entry):
    """Whether npm installs this lockfile entry on this machine: its os/cpu lists (with '!' exclusions) admit it."""
    plat = {"win32": "win32", "darwin": "darwin"}.get(sys.platform, "linux" if sys.platform.startswith("linux") else sys.platform)
    cpu = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(__import__("platform").machine().lower(), "x64")
    for field, here in (("os", plat), ("cpu", cpu)):
        allowed = entry.get(field)
        if not allowed:
            continue
        allowed = [allowed] if isinstance(allowed, str) else allowed
        if f"!{here}" in allowed or (any(not a.startswith("!") for a in allowed) and here not in allowed):
            return False
    return True


def npm_entries(lock):
    """[(name, version, integrity or None)] for each registry package in a package-lock.json (v1, v2 or v3)."""
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for key, entry in (data.get("packages") or {}).items():
        if not key or not isinstance(entry, dict) or entry.get("link") or entry.get("inBundle"):
            continue
        resolved = str(entry.get("resolved", ""))
        if resolved and not resolved.startswith(("http://", "https://")):
            continue                             # a local file or git dependency is project code, not a registry package
        name = entry.get("name") or key.split("node_modules/")[-1]
        if entry.get("optional") and not _this_platform(entry):
            continue        # a native build for another OS or CPU (rolldown's android/darwin bindings): npm never fetches it here
        out.append((name, entry.get("version", ""), entry.get("integrity")))
    if not out and isinstance(data.get("dependencies"), dict):
        stack = list(data["dependencies"].items())
        while stack:
            name, entry = stack.pop()
            if isinstance(entry, dict):
                out.append((name, entry.get("version", ""), entry.get("integrity")))
                stack += list((entry.get("dependencies") or {}).items())
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def cache_holds(cache, integrity):
    """npm's cache (cacache) stores content under content-v2/<algorithm>/<hex digest split 2/2/rest>."""
    for item in str(integrity or "").split():
        algo, _, b64 = item.partition("-")
        try:
            digest = base64.b64decode(b64).hex()
        except ValueError:
            continue
        for base in (cache, cache / "_cacache"):      # npm puts cacache under _cacache/ inside the --cache folder
            if (base / "content-v2" / algo / digest[:2] / digest[2:4] / digest[4:]).is_file():
                return True
    return False


def problems(root, files, source_dir=DEFAULT_DIR):
    """What stops this project's packages being verified and installed with no network."""
    root = pathlib.Path(root)
    source = root / source_dir
    out, needs_source = [], False
    held = {}
    if source.is_dir():
        for f in source.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".whl", ".gz", ".zip"):
                held[sha256(f)] = f
    for f in files:
        rel = f.relative_to(root).as_posix()
        if REQ_FILE.match(f.name):
            for req, name, version, hashes in requirement_pins(f):
                needs_source = True
                if not hashes:
                    out.append(f"{rel}: '{req}' carries no --hash: pip cannot verify the file it installs; "
                               f"run `deps lock` to pin hashes and fill {source_dir}/")
                elif source.is_dir() and not any(h in held for h in hashes):
                    out.append(f"{rel}: {name}=={version} is not in {source_dir}/ with a matching hash: "
                               "the project cannot be built disconnected")
        elif f.name in ("package-lock.json", "npm-shrinkwrap.json"):
            for name, version, integrity in npm_entries(f):
                needs_source = True
                if not integrity:
                    out.append(f"{rel}: {name}@{version} has no integrity hash: npm cannot verify what it installs")
                elif source.is_dir() and not cache_holds(source / "npm-cache", integrity):
                    out.append(f"{rel}: {name}@{version} is not in {source_dir}/npm-cache: "
                               "the project cannot be built disconnected (run `deps fetch` while connected)")
    if needs_source and not source.is_dir():
        out.insert(0, f"third-party packages with no offline package source ({source_dir}/): the project cannot be built "
                      "disconnected; run `deps lock` / `deps fetch` once while connected")
    return out


def lock_python(root, requirements_in, out_txt, source_dir=DEFAULT_DIR, run=subprocess.run):
    """Resolve requirements_in (exact pins) into source_dir with pip, then write out_txt pinning every downloaded
    distribution, dependencies included, to its sha256. Needs the network once."""
    root = pathlib.Path(root)
    source = root / source_dir
    source.mkdir(parents=True, exist_ok=True)
    res = run([sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "-d", str(source), "-r",
               str(root / requirements_in)], capture_output=True, text=True)
    if res.returncode != 0:
        return False, (res.stderr or res.stdout)[-400:]
    lines = []
    for f in sorted(source.iterdir()):
        m = DIST.match(f.name)
        if f.is_file() and m:
            lines.append(f"{m.group('name').replace('_', '-')}=={m.group('version')} \\\n    --hash=sha256:{sha256(f)}")
    (root / out_txt).write_text("# generated by `deps lock` from " + requirements_in + "; install with\n"
                                "# pip install --no-index --find-links " + source_dir + " --require-hashes -r " + out_txt + "\n"
                                + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return True, f"{len(lines)} distribution(s) pinned with hashes in {out_txt}; files held in {source_dir}/"


def fetch_npm(root, source_dir=DEFAULT_DIR, npm="npm", run=subprocess.run):
    """Fill source_dir/npm-cache from package-lock.json with npm itself (no install scripts run). Needs the network once;
    afterwards `npm ci --offline --cache <source_dir>/npm-cache` installs disconnected."""
    root = pathlib.Path(root)
    cache = root / source_dir / "npm-cache"
    cache.mkdir(parents=True, exist_ok=True)
    # every package-lock.json in the project, not only one at the root (honey-do keeps its frontend in frontend/)
    homes = sorted({p.parent for p in root.rglob("package-lock.json")
                    if "node_modules" not in p.parts and source_dir not in p.relative_to(root).parts}) or [root]
    for home in homes:
        res = run([npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund", "--cache", str(cache)], cwd=str(home),
                  capture_output=True, text=True, shell=sys.platform == "win32")
        if res.returncode != 0:
            return False, (res.stderr or res.stdout)[-400:]
    return True, f"npm cache filled at {source_dir}/npm-cache from {len(homes)} lockfile folder(s)"
