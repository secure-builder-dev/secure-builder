# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Offline bundles and ingest records (spec 04 §4.1, §4.2, §10.2.4, §10.5).

Scanner images and detection data cross a boundary as dated bundles with
provenance — source side, identifier, content hash, production date, operator.
Ingestion verifies the hash and writes a record. A hash mismatch is not one
thing: a cross-domain filter that modified the content is routine and needs a
re-send or a recorded, understood exemption; a bundle that is simply wrong is
an integrity incident. The two are told apart and never treated alike, and a
filtered bundle is never ingested on the assumption the filtering was benign.
"""
import datetime
import hashlib
import json
import pathlib
import shutil
import tarfile

from .. import tools
from ..records import now, table
from ..records import schema as sch
from . import images
from .runner import DATA_DATE, DB_VOLUME

INGEST_RECORD = ".engine/records/ingest-records.md"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest(kind, files, cfg, operator, extra=None):
    data = {"kind": kind, "produced": datetime.date.today().isoformat(), "source_side": cfg.side if cfg else "unknown",
            "operator": operator, "files": files, "harness_pins": {c: ref for c, (_, ref, _) in images.SCANNERS.items()}}
    data.update(extra or {})
    data["bundle_id"] = f"{kind}-{data['produced']}-{hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:8]}"
    return data


def bundle_images(root, out_dir, cfg, operator, invoke=None):
    """Export every pinned scanner image as an archive with its digest recorded."""
    if cfg and cfg.mode == "disconnected":
        raise RuntimeError("image bundles are produced on a connected machine; this instance is disconnected")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    invoke = invoke or (lambda args: tools.run_tool("docker", args, timeout=1800))
    files = {}
    for concern, (tool, ref, _) in images.SCANNERS.items():
        if invoke(["pull", ref]).exit_code != 0:
            raise RuntimeError(f"pull of {ref} failed")
        name = f"{tool}.tar"
        if invoke(["save", "-o", str(out / name), ref]).exit_code != 0:
            raise RuntimeError(f"save of {ref} failed")
        insp = invoke(["image", "inspect", "--format", "{{index .RepoDigests 0}}", ref])
        files[name] = {"image": ref, "digest": insp.stdout.strip(), "sha256": sha256(out / name)}
    data = _manifest("scanner-images", files, cfg, operator)
    (out / "manifest.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def bundle_data(root, out_dir, cfg, operator):
    """Package the shared detection-data store with its production date and hash. Scriptable."""
    src = pathlib.Path(root) / DB_VOLUME
    if not src.is_dir() or not any(src.iterdir()):
        raise RuntimeError(f"{DB_VOLUME} holds no detection data to bundle")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tar = out / "detection-data.tar"
    with tarfile.open(tar, "w") as tf:
        tf.add(src, arcname="clamav-db")
    files = {"detection-data.tar": {"sha256": sha256(tar)}}
    data = _manifest("detection-data", files, cfg, operator)
    (out / "manifest.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def verify(bundle_dir):
    """Return (manifest, [(file, ok, reason)])."""
    d = pathlib.Path(bundle_dir)
    m = d / "manifest.json"
    if not m.is_file():
        raise RuntimeError("bundle carries no manifest.json")
    data = json.loads(m.read_text(encoding="utf-8"))
    results = []
    for name, meta in data.get("files", {}).items():
        p = d / name
        if not p.is_file():
            results.append((name, False, "file absent from bundle"))
        elif sha256(p) != meta.get("sha256"):
            results.append((name, False, "content hash differs from the manifest"))
        else:
            results.append((name, True, "hash verified"))
    return data, results


def _record(root, cfg, data, hash_result, modified, operator):
    if not (pathlib.Path(root) / INGEST_RECORD).is_file():
        return
    table.append(root, INGEST_RECORD, sch.INGEST, {
        "date": now(cfg), "bundle": data.get("bundle_id", "?"), "production_date": data.get("produced", "?"),
        "arrival_date": datetime.date.today().isoformat(), "hash_result": hash_result, "modified_in_transit": modified,
        "operator": operator, "side": cfg.side if cfg else sch.UNKNOWN})


def ingest(root, bundle_dir, cfg, operator, filtered_understood="", invoke=None):
    """Ingest an image or data bundle. Refuses on hash mismatch unless the filtering is
    understood and recorded; distinguishes the two mismatch cases in what it says."""
    data, results = verify(bundle_dir)
    bad = [r for r in results if not r[1]]
    if bad:
        detail = "; ".join(f"{n}: {why}" for n, _, why in bad)
        if not filtered_understood.strip():
            _record(root, cfg, data, f"MISMATCH ({detail})", "unknown — refused", operator)
            raise RuntimeError("hash mismatch — bundle refused. Two cases look identical here and are not: the boundary "
                               "filtered the content (routine: re-request, or ingest with the filtering understood and recorded) "
                               "or the bundle is wrong (an integrity incident). " + detail)
        _record(root, cfg, data, f"MISMATCH ({detail})", f"yes — understood: {filtered_understood.strip()}", operator)
    else:
        _record(root, cfg, data, "verified", "no", operator)
    d = pathlib.Path(bundle_dir)
    if data.get("kind") == "scanner-images":
        invoke = invoke or (lambda args: tools.run_tool("docker", args, timeout=1800))
        for name in data["files"]:
            if invoke(["load", "-i", str(d / name)]).exit_code != 0:
                raise RuntimeError(f"load of {name} failed")
    elif data.get("kind") == "detection-data":
        dest = pathlib.Path(root) / DB_VOLUME
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(d / "detection-data.tar") as tf:
            tf.extractall(dest.parent, filter="data")
        (pathlib.Path(root) / DATA_DATE).write_text(data["produced"] + "\n", encoding="utf-8", newline="\n")
    else:
        raise RuntimeError(f"unknown bundle kind {data.get('kind')!r}")
    return data


def images_present(invoke=None):
    """Which pinned scanner images are present locally (for disconnected mode: no pull, ever)."""
    invoke = invoke or (lambda args: tools.run_tool("docker", args, timeout=120))
    missing = []
    for concern, (tool, ref, _) in images.SCANNERS.items():
        if invoke(["image", "inspect", ref]).exit_code != 0:
            missing.append(f"{concern}: {ref} is not present locally — a missing image is a failure, never a skip")
    return missing
