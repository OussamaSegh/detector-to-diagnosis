#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""tools/platform_check.py (Chapter 25): a conforming system has no deviation, each kind of
difference is found and named, and the platform SBOM is valid CycloneDX 1.5.
"""
import copy
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import platform_check  # noqa: E402

REPO = TOOLS.parent
DEFINITION = json.loads((REPO / "platform" / "platform.json").read_text())


def conforming():
    """The facts of a system installed exactly as the definition says."""
    return {
        "distribution": "ubuntu", "release": "24.04", "architecture": "amd64", "kernel": "6.8.0-52-generic",
        "cmdline": ["BOOT_IMAGE=/vmlinuz", "ro"] + DEFINITION["kernel"]["cmdline"],
        "packages": {p["name"]: p["version"] for p in DEFINITION["packages"]},
        "sysctl": dict(DEFINITION["sysctl"]),
        "users": {u: True for u in DEFINITION["users"]},
        "files": {f["target"]: hashlib.sha256((REPO / f["source"]).read_bytes()).hexdigest()
                  for f in DEFINITION["files"]},
        "platform_id": DEFINITION["id"],
    }


class PlatformCheck(unittest.TestCase):
    def test_a_conforming_system_has_no_deviation(self):
        self.assertEqual(platform_check.check(DEFINITION, conforming()), [])

    def test_every_kind_of_difference_is_one_named_deviation(self):
        changes = {
            "kernel": lambda f: f.update(kernel="6.18.44-fc"),
            "package libssl3t64": lambda f: f["packages"].update({"libssl3t64": "3.0.13-0ubuntu3.17"}),
            "package tar": lambda f: f["packages"].update({"tar": None}),
            "sysctl net.core.rmem_max": lambda f: f["sysctl"].update({"net.core.rmem_max": "212992"}),
            "user minidaq": lambda f: f["users"].update({"minidaq": False}),
            "file /etc/systemd/system/minidaq.service": lambda f: f["files"].update(
                {"etc/systemd/system/minidaq.service": "0" * 64}),
            "platform id": lambda f: f.update(platform_id="minidaq-platform-0"),
            "release": lambda f: f.update(release="22.04"),
            "kernel command line: nohz_full": lambda f: f.update(cmdline=["isolcpus=1-3"]),
        }
        for what, change in changes.items():
            facts = copy.deepcopy(conforming())
            change(facts)
            deviations = platform_check.check(DEFINITION, facts)
            self.assertEqual(len(deviations), 1, (what, deviations))
            self.assertTrue(deviations[0].startswith(what), (what, deviations))

    def test_the_files_are_read_under_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for f in DEFINITION["files"]:
                (root / f["target"]).parent.mkdir(parents=True, exist_ok=True)
                (root / f["target"]).write_bytes((REPO / f["source"]).read_bytes())
            (root / DEFINITION["platform_id_file"]).parent.mkdir(parents=True, exist_ok=True)
            (root / DEFINITION["platform_id_file"]).write_text(DEFINITION["id"] + "\n")
            facts = platform_check.collect(DEFINITION, root)
            self.assertEqual(facts["files"], conforming()["files"])
            self.assertEqual(facts["platform_id"], DEFINITION["id"])

    def test_the_platform_sbom_is_valid_cyclonedx(self):
        try:
            import jsonschema  # noqa: F401
            import referencing  # noqa: F401  (jsonschema 4.18 and later; make_sbom.validate needs it)
        except ImportError:
            self.skipTest("jsonschema 4.18 or later is not installed")
        import make_sbom
        bom = platform_check.sbom(DEFINITION, conforming())
        self.assertEqual(make_sbom.validate(bom, TOOLS / "sbom" / "schemas"), 0)
        purls = [c.get("purl") for c in bom["components"]]
        self.assertIn("pkg:deb/ubuntu/libssl3t64@3.0.13-0ubuntu3.16?arch=amd64&distro=ubuntu-24.04", purls)


if __name__ == "__main__":
    unittest.main()
