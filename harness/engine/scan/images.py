# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The scanner image set — the single file where a tool version is a one-line
change (spec 01 REQ-4.2.1, §4.3).

Every reference carries an explicit tag or digest. Scanners that download
their detection data at run time may be pinned to a digest or an immutable
tag. A scanner whose detection data is *embedded in the image* is pinned to a
moving tag and never to a digest or a patch version: an immutable patch tag is
a digest wearing a tag's clothes, and pinning it freezes the signatures
forever. The pin rule is enforced mechanically (REQ-4.3.3).
"""
import re

# concern -> (tool name, image reference, detection data embedded in the image?)
SCANNERS = {
    "container-hygiene": ("hadolint", "docker.io/hadolint/hadolint:v2.12.0", False),
    "iac-misconfiguration": ("trivy-config", "docker.io/aquasec/trivy:0.75.0", False),
    "malware": ("clamav", "docker.io/clamav/clamav:1.4", True),
    "vulnerabilities-a": ("trivy", "docker.io/aquasec/trivy:0.75.0", False),
    "vulnerabilities-b": ("grype", "docker.io/anchore/grype:v0.86.1", False),
    "composition": ("syft", "docker.io/anchore/syft:v1.18.1", False),
    # static analysis of the project's own code: two independent analyzers, as for dependencies
    "sast-a": ("semgrep", "docker.io/semgrep/semgrep:1.179.0", False),
    "sast-b": ("bandit", "ghcr.io/pycqa/bandit/bandit:1.9.4", False),
}
# the executable each concern runs under the host engine (no container runtime): the image's tool name is
# not always a program on the path (trivy-config is trivy; the malware scanner is clamscan and freshclam)
HOST_EXECUTABLES = {"hadolint": "hadolint", "trivy-config": "trivy", "clamav": "clamscan", "trivy": "trivy",
                    "grype": "grype", "syft": "syft", "semgrep": "semgrep", "bandit": "bandit"}
REQUIRED_CONCERNS = ("container-hygiene", "iac-misconfiguration", "malware", "vulnerabilities-a", "vulnerabilities-b",
                     "sast-a", "sast-b")

DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
TAG = re.compile(r":([^/@:]+)$")
PATCH_TAG = re.compile(r"^v?\d+\.\d+\.\d+([.-].*)?$")


def pin_problems(scanners=None):
    out = []
    for concern, (tool, ref, embedded) in (SCANNERS if scanners is None else scanners).items():
        has_digest = bool(DIGEST.search(ref))
        m = TAG.search(ref.split("@")[0])
        tag = m.group(1) if m else None
        if not has_digest and not tag:
            out.append(f"{concern} ({tool}): {ref} carries neither a tag nor a digest")
            continue
        if embedded:
            if has_digest:
                out.append(f"{concern} ({tool}): embedded detection data pinned to a digest — signatures frozen at build time")
            elif tag and PATCH_TAG.match(tag):
                out.append(f"{concern} ({tool}): embedded detection data pinned to immutable patch tag {tag} — a digest wearing a tag's clothes")
    return out
