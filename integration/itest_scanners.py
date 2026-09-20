# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Integration tier (spec 05 §6.1): the real scanner containers, exercised for
the properties the hermetic tier can only stub. Runs only under
`python -m engine integration`, only where a container runtime is usable, and
gates a release — never a push. Each test names the exact exit code or output
shape it relies on; anything else is the tool falling over."""
import json
import pathlib
import re
import tempfile
import unittest

from engine import tools
from engine.scan import images, runner

EICAR = "X5O!P%@AP[4" + chr(92) + "PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def docker(args, timeout=1800):
    rt = runner.runtime_usable()
    return tools.run_tool(rt, args, timeout=timeout)


class PinnedImagesExist(unittest.TestCase):
    def test_every_pinned_image_pulls(self):
        for concern, (tool, ref, _) in images.SCANNERS.items():
            res = docker(["pull", ref])
            self.assertEqual(res.exit_code, 0, f"{concern}: {ref} did not pull: {res.stderr[-200:]}")


class Malware(unittest.TestCase):
    def test_version_line_carries_a_parseable_signature_date(self):
        tool, ref, _ = images.SCANNERS["malware"]
        res = docker(["run", "--rm", ref, "clamscan", "--version"])
        self.assertEqual(res.exit_code, 0, res.stderr)
        self.assertRegex(res.stdout.strip(), r"^ClamAV [\d.]+/\d+/.+$")

    def test_eicar_is_exit_code_one_exactly(self):
        tool, ref, _ = images.SCANNERS["malware"]
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "eicar.txt").write_text(EICAR, encoding="ascii")
            res = docker(["run", "--rm", "-v", f"{d}:/src", ref, "clamscan", "-r", "--infected", "/src"])
            self.assertEqual(res.exit_code, 1, "1 means detection; anything else is the scanner falling over")
            self.assertRegex(res.stdout, r"eicar\.txt: .*FOUND")

    def test_clean_directory_is_exit_code_zero(self):
        tool, ref, _ = images.SCANNERS["malware"]
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "hello.txt").write_text("hello", encoding="ascii")
            res = docker(["run", "--rm", "-v", f"{d}:/src", ref, "clamscan", "-r", "--infected", "/src"])
            self.assertEqual(res.exit_code, 0)


class Vulnerability(unittest.TestCase):
    IMAGE = "docker.io/library/alpine:3.18.0"

    def test_trivy_and_grype_both_produce_parseable_json(self):
        docker(["pull", self.IMAGE])
        _, trivy, _ = images.SCANNERS["vulnerabilities-a"]
        _, grype, _ = images.SCANNERS["vulnerabilities-b"]
        res = docker(["run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock", trivy, "image", "--format", "json", self.IMAGE])
        self.assertEqual(res.exit_code, 0, res.stderr[-300:])
        data = json.loads(res.stdout)
        self.assertIn("Results", data)
        res = docker(["run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock", grype, self.IMAGE, "-o", "json"])
        self.assertEqual(res.exit_code, 0, res.stderr[-300:])
        data = json.loads(res.stdout)
        self.assertIn("matches", data)

    def test_syft_produces_cyclonedx(self):
        _, syft, _ = images.SCANNERS["composition"]
        res = docker(["run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock", syft, self.IMAGE, "-o", "cyclonedx-json"])
        self.assertEqual(res.exit_code, 0, res.stderr[-300:])
        self.assertEqual(json.loads(res.stdout).get("bomFormat"), "CycloneDX")


class Hygiene(unittest.TestCase):
    def test_hadolint_flags_a_known_bad_dockerfile(self):
        _, ref, _ = images.SCANNERS["container-hygiene"]
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "Dockerfile").write_text("FROM ubuntu:latest" + chr(10) + "RUN apt-get install curl" + chr(10), encoding="ascii")
            res = docker(["run", "--rm", "-v", f"{d}:/src", ref, "hadolint", "-f", "json", "/src/Dockerfile"])
            self.assertEqual(res.exit_code, 1, "1 means findings")
            self.assertTrue(any(i.get("code", "").startswith("DL") for i in json.loads(res.stdout)))
