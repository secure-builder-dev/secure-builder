# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Standards catalogues (spec 01 §8.2, §8.4; spec 04 §3; spec 06 REQ-8.5).

A catalogue is a vendored, version-pinned lookup table: identifier, status
(active or withdrawn), official title, and for withdrawn entries the
identifiers that superseded it. No full control text; no retrieval; the one
question it answers is whether an identifier resolves to a real, current
control, deterministically. Each catalogue carries provenance — source
location, source content hash, catalogue version, retrieval timestamp — and a
statement of the terms under which it is redistributed, or that the operator
must supply it.

Adopting a newer catalogue is an explicit, reviewable action that produces a
diff. Ingest refuses a document carrying handling markings unless the operator
acknowledges. Only the currency command reaches the network, and never in
disconnected mode.
"""
import datetime
import hashlib
import json
import pathlib
import re
import tarfile

from . import net

DIR = ".engine/catalogues"
CURRENCY_FILE = ".engine/currency-verified"
MARKINGS = re.compile(r"(?im)^\s*(CUI|FOUO|CONTROLLED UNCLASSIFIED INFORMATION|(?:TOP )?SECRET|CONFIDENTIAL)(//|\b)")
STATUSES = ("active", "withdrawn")


class CatalogueError(Exception):
    pass


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_all(root):
    """{catalogue key: catalogue dict} for every vendored catalogue with valid provenance."""
    d = pathlib.Path(root) / DIR
    out = {}
    if not d.is_dir():
        return out
    for prov in sorted(d.glob("*.provenance.json")):
        try:
            meta = json.loads(prov.read_text(encoding="utf-8"))
            data_file = d / meta["file"]
            raw = data_file.read_bytes()
            if sha256_bytes(raw) != meta["sha256"]:
                raise CatalogueError(f"{data_file.name}: content hash differs from its provenance")
            cat = json.loads(raw.decode("utf-8"))
            cat["_provenance"] = meta
            out[cat["key"]] = cat
        except (OSError, ValueError, KeyError) as e:
            raise CatalogueError(f"{prov.name}: unreadable ({type(e).__name__}: {e})")
    return out


def problems(cat):
    out = []
    for k in ("key", "publication", "revision", "entries"):
        if k not in cat:
            out.append(f"catalogue lacks '{k}'")
    if out:
        return out
    for ident, e in cat["entries"].items():
        if e.get("status") not in STATUSES:
            out.append(f"{ident}: status must be active or withdrawn")
        if not e.get("title"):
            out.append(f"{ident}: no official title")
        if e.get("status") == "withdrawn" and not e.get("superseded_by"):
            out.append(f"{ident}: withdrawn without naming what superseded it")
        if "text" in e:
            out.append(f"{ident}: catalogues do not store control text")
    return out


def write(root, cat, source, source_sha256, retrieved, terms):
    """Vendor a catalogue with its provenance. Returns (data path, provenance path)."""
    probs = problems(cat)
    if probs:
        raise CatalogueError("; ".join(probs))
    d = pathlib.Path(root) / DIR
    d.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(cat, indent=1, sort_keys=True) + "\n").encode("utf-8")
    data = d / f"{cat['key']}.json"
    data.write_bytes(raw)
    prov = {"file": data.name, "sha256": sha256_bytes(raw), "source": source, "source_sha256": source_sha256,
            "version": f"{cat['publication']} {cat['revision']}", "retrieved": retrieved, "redistribution": terms}
    p = d / f"{cat['key']}.provenance.json"
    p.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data, p


def diff(old, new):
    """Human-readable differences between two catalogues of the same key."""
    lines = []
    oe, ne = old.get("entries", {}), new.get("entries", {})
    for ident in sorted(set(oe) | set(ne)):
        a, b = oe.get(ident), ne.get(ident)
        if a is None:
            lines.append(f"+ {ident}: {b.get('status')} — {b.get('title')}")
        elif b is None:
            lines.append(f"- {ident}: no longer listed")
        elif a != b:
            lines.append(f"~ {ident}: {a.get('status')} '{a.get('title')}' -> {b.get('status')} '{b.get('title')}'"
                         + (f" (superseded by {', '.join(b.get('superseded_by', []))})" if b.get("superseded_by") else ""))
    if old.get("revision") != new.get("revision"):
        lines.insert(0, f"~ revision: {old.get('revision')} -> {new.get('revision')}")
    return lines


def from_oscal(text):
    """Convert an official OSCAL catalog JSON document into the vendored shape."""
    doc = json.loads(text)
    cat = doc.get("catalog") or doc
    meta = cat.get("metadata", {})
    entries = {}

    def walk(controls):
        for c in controls or []:
            ident = c.get("id", "").upper().replace(".", "(") + (")" if "." in c.get("id", "") else "")
            ident = re.sub(r"^([A-Z]+)-0*(\d+)", r"\1-\2", ident)
            props = {p.get("name"): p.get("value") for p in c.get("props", []) or []}
            status = "withdrawn" if props.get("status", "").lower() == "withdrawn" else "active"
            superseded = []
            for link in c.get("links", []) or []:
                if link.get("rel") in ("incorporated-into", "moved-to"):
                    superseded.append(link.get("href", "").lstrip("#").upper())
            entries[ident] = {"status": status, "title": c.get("title", ""), **({"superseded_by": superseded} if status == "withdrawn" else {})}
            walk(c.get("controls"))

    for g in cat.get("groups", []) or []:
        walk(g.get("controls"))
    walk(cat.get("controls"))
    version = meta.get("version", "")
    return {"key": "nist-sp-800-53-r5", "publication": "NIST SP 800-53", "revision": f"Rev {version.split('.')[0] if version else '?'}",
            "published_revisions": ["Rev 4", "Rev 5"], "entries": entries}


def ingest(root, path, acknowledge_markings=False, source=None, terms=None):
    """Adopt a catalogue document supplied by the operator: OSCAL or the vendored shape.
    Refuses handling markings unless acknowledged. Returns the diff against the previous version."""
    p = pathlib.Path(path)
    raw = p.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    m = MARKINGS.search(text)
    if m and not acknowledge_markings:
        raise CatalogueError(f"document carries a handling marking ({m.group(1).strip()}); ingest refused unless the operator "
                             "explicitly acknowledges that this repository is cleared for it")
    try:
        cat = from_oscal(text) if '"catalog"' in text[:2000] or '"groups"' in text[:5000] else json.loads(text)
    except ValueError as e:
        raise CatalogueError(f"not a catalogue document: {e}")
    if "_provenance" in cat:
        del cat["_provenance"]
    existing = load_all(root)
    old = existing.get(cat.get("key"), {"entries": {}, "revision": None})
    write(root, cat, source or f"operator-supplied: {p.name}", sha256_bytes(raw),
          datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
          terms or "operator-supplied; redistribution terms as the operator recorded them")
    return diff(old, cat)


# --- transfer bundle (spec 04 §3.5–3.7) ---

def bundle(root, out_dir):
    d = pathlib.Path(root) / DIR
    cats = load_all(root)
    if not cats:
        raise CatalogueError("no vendored catalogues to bundle")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tar = out / "catalogues.tar"
    with tarfile.open(tar, "w") as tf:
        for f in sorted(d.glob("*.json")):
            tf.add(f, arcname=f.name)
    manifest = {"kind": "catalogues", "produced": datetime.date.today().isoformat(), "sha256": sha256_bytes(tar.read_bytes()),
                "catalogues": {k: {"version": c["_provenance"]["version"], "source": c["_provenance"]["source"]} for k, c in cats.items()}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def ingest_bundle(root, bundle_dir):
    """Verify the hash, then adopt each catalogue in the bundle; returns {key: diff lines}. Not automatic: the caller shows the diff."""
    b = pathlib.Path(bundle_dir)
    manifest = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
    tar = b / "catalogues.tar"
    if sha256_bytes(tar.read_bytes()) != manifest["sha256"]:
        raise CatalogueError("catalogue bundle hash does not match its manifest — refused")
    existing = load_all(root)
    diffs = {}
    with tarfile.open(tar) as tf:
        for member in tf.getmembers():
            if not member.name.endswith(".json") or member.name.endswith(".provenance.json"):
                continue
            cat = json.loads(tf.extractfile(member).read().decode("utf-8"))
            key = cat["key"]
            prov_member = next((m for m in tf.getmembers() if m.name == f"{key}.provenance.json"), None)
            prov = json.loads(tf.extractfile(prov_member).read().decode("utf-8")) if prov_member else {}
            old = existing.get(key, {"entries": {}, "revision": None})
            diffs[key] = diff(old, cat)
            write(root, cat, prov.get("source", "bundle"), prov.get("source_sha256", ""), prov.get("retrieved", manifest["produced"]),
                  prov.get("redistribution", "as bundled"))
    return diffs


# --- currency (spec 01 §8.4; spec 04 §3.2–3.4, §3.8) ---

SOURCES = {
    "nist-sp-800-53-r5": "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json",
}


def currency(root, cfg, offline=False, fetch=None):
    """Report whether vendored pins are current. In disconnected mode, or with the
    offline flag, reports 'currency not checked' and exits successfully — never current.
    A fetch in disconnected mode without the flag is an error, not a fallback."""
    mode = cfg.mode if cfg else "local"
    cats = load_all(root)
    lines = []
    if not cats:
        return ["currency: no vendored catalogues"], 2
    if offline:
        lines.append("currency: NOT CHECKED — offline flag; vendored pins were not compared to published sources")
        lines.append(_elapsed_line(root))
        return lines, 0
    if mode == "disconnected":
        return ["currency: ERROR — mode is disconnected; a fetch is not attempted. Pass the offline flag to report "
                "'currency not checked' explicitly, or ingest a catalogue bundle"], 1
    fetch = fetch or (lambda url: net.fetch(url, mode=mode, caller="currency"))
    stale = 0
    for key, cat in cats.items():
        url = SOURCES.get(key)
        if not url:
            lines.append(f"currency: {key}: no published source is indexed for this catalogue — not checked")
            continue
        try:
            raw = fetch(url)
        except Exception as e:
            lines.append(f"currency: {key}: fetch failed ({type(e).__name__}) — NOT CHECKED")
            continue
        published = sha256_bytes(raw)
        pinned = cat["_provenance"].get("source_sha256", "")
        if published == pinned:
            lines.append(f"currency: {key}: pinned source hash matches the published catalogue — current")
        else:
            stale += 1
            lines.append(f"currency: {key}: published catalogue differs from the pinned source (pinned {pinned[:12]}…, published {published[:12]}…) — "
                         "adopt it deliberately with `catalogue ingest`; nothing is adopted automatically")
    (pathlib.Path(root) / CURRENCY_FILE).write_text(datetime.date.today().isoformat() + "\n", encoding="utf-8", newline="\n")
    lines.append(_elapsed_line(root))
    return lines, 0 if not stale else 3


def _elapsed_line(root):
    p = pathlib.Path(root) / CURRENCY_FILE
    if not p.is_file():
        return "currency: last successful verification: never"
    try:
        d = datetime.date.fromisoformat(p.read_text(encoding="utf-8").strip()[:10])
    except ValueError:
        return "currency: last successful verification: unreadable"
    return f"currency: last successful verification {d.isoformat()}, {(datetime.date.today() - d).days} day(s) ago"
