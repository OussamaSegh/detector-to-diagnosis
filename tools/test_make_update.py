#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""tools/make_update.py and minidaq_update end to end (Chapter 25): a bundle built and signed on
the release side installs, is confirmed or rolled back on the acquisition side, and is the same
bytes when it is built twice.

Usage: test_make_update.py MINIDAQ_UPDATE
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent
UPDATE = None


def run(*args, ok=True, env=None):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env)
    if ok and r.returncode != 0:
        raise AssertionError(f"{args} -> {r.returncode}\n{r.stdout}{r.stderr}")
    return r


class MakeUpdate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="minidaq-mu-")
        self.tmp = pathlib.Path(self._tmp.name)
        self.key = self.tmp / "release.key"  # exists only for this test
        run("openssl", "genpkey", "-algorithm", "ed25519", "-out", self.key)
        (self.tmp / "keys").mkdir()
        run("openssl", "pkey", "-in", self.key, "-pubout", "-out", self.tmp / "keys" / "release.pem")
        (self.tmp / "platform-id").write_text("minidaq-platform-1\n")
        self.root = self.tmp / "opt"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def bundle(self, version, out=None, epoch="1700000000"):
        stage = self.tmp / f"stage-{version}"
        (stage / "bin").mkdir(parents=True, exist_ok=True)
        (stage / "share" / "minidaq").mkdir(parents=True, exist_ok=True)
        server = stage / "bin" / "minidaq_server"
        server.write_text(f"#!/bin/sh\necho {version}\n")
        server.chmod(0o755)
        (stage / "share" / "minidaq" / "VERSION").write_text(version + "\n")
        out = out or self.tmp / f"bundle-{version}"
        run(sys.executable, TOOLS / "make_update.py", "--stage", stage, "--version", version, "--commit", "abc1234",
            "--platform", "minidaq-platform-1", "--key", self.key, "--out", out,
            env=dict(os.environ, SOURCE_DATE_EPOCH=epoch))
        return out

    def update(self, *args, ok=True):
        return run(UPDATE, *args, "--root", self.root, ok=ok)

    def install(self, bundle, ok=True):
        return run(UPDATE, "install", bundle, "--root", self.root, "--keys", self.tmp / "keys",
                   "--platform-file", self.tmp / "platform-id", ok=ok)

    def status(self):
        return json.loads(self.update("status").stdout)

    def test_a_bundle_installs_and_its_trial_is_confirmed_or_rolled_back(self):
        # REQ: SRS-PLT-003, SRS-PLT-006, SRS-PLT-010
        self.install(self.bundle("0.5.0"))
        self.assertEqual(run(self.root / "current" / "bin" / "minidaq_server").stdout, "0.5.0\n")
        self.install(self.bundle("0.5.1"))
        self.assertEqual(self.status()["trial"], {"slot": "b", "version": "0.5.1"})
        self.assertEqual(run(self.root / "current" / "bin" / "minidaq_server").stdout, "0.5.1\n")
        self.assertEqual(self.update("rollback").returncode, 0)
        self.assertEqual(run(self.root / "current" / "bin" / "minidaq_server").stdout, "0.5.0\n")
        self.assertEqual(self.update("rollback", ok=False).returncode, 3, "nothing to roll back")
        self.install(self.bundle("0.5.2"))
        self.update("confirm")
        self.assertEqual(self.status()["good"], {"slot": "b", "version": "0.5.2"})
        self.assertIsNone(self.status()["trial"])

    def test_a_bundle_is_refused_unless_its_signature_and_platform_check(self):
        # REQ: SRS-PLT-003
        b = self.bundle("0.5.0")
        (self.tmp / "platform-id").write_text("another-platform\n")
        r = self.install(b, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("for the platform", r.stderr)
        (self.tmp / "platform-id").write_text("minidaq-platform-1\n")
        manifest = json.loads((b / "update.json").read_text())
        manifest["version"] = "9.9.9"  # a version the signer did not sign
        (b / "update.json").write_text(json.dumps(manifest, indent=2) + "\n")
        r = self.install(b, ok=False)
        self.assertIn("does not verify", r.stderr)
        self.assertFalse((self.root / "current").exists())

    def test_the_same_tree_gives_the_same_bundle(self):
        # REQ: SRS-PLT-003
        a = self.bundle("0.5.0", self.tmp / "one")
        b = self.bundle("0.5.0", self.tmp / "two")
        self.assertEqual((a / "minidaq-0.5.0.tar.gz").read_bytes(), (b / "minidaq-0.5.0.tar.gz").read_bytes())
        self.assertEqual((a / "update.json").read_bytes(), (b / "update.json").read_bytes())
        # Ed25519 signatures are deterministic too (RFC 8032).
        self.assertEqual((a / "update.json.sig").read_bytes(), (b / "update.json.sig").read_bytes())


if __name__ == "__main__":
    UPDATE = pathlib.Path(sys.argv.pop(1)).resolve()
    unittest.main()
