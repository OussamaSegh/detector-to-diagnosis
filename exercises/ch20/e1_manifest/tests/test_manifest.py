# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 20.1. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import manifest as m


def package(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


FILES = {"bin/minidaq_server": "server\n", "bin/minidaq_ctl": "client\n", "BUILDINFO.json": "{}\n",
         "debug/minidaq_server.debug": "debug\n"}


class Manifest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.top = package(self.tmp / "a", FILES)
        self.paths = m.write_manifest(self.top)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_every_file_is_listed_once_and_sorted(self):
        self.assertEqual(self.paths, sorted(FILES))
        lines = (self.top / m.NAME).read_text().splitlines()
        self.assertEqual([line.split("  ", 1)[1] for line in lines], sorted(FILES))

    def test_sha256sum_accepts_it(self):
        if shutil.which("sha256sum") is None:
            self.skipTest("no sha256sum")
        p = subprocess.run(["sha256sum", "--quiet", "-c", m.NAME], cwd=self.top, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_the_same_files_give_the_same_manifest(self):
        other = package(self.tmp / "b", dict(reversed(list(FILES.items()))))
        m.write_manifest(other)
        self.assertEqual((other / m.NAME).read_bytes(), (self.top / m.NAME).read_bytes())

    def test_an_intact_package_verifies(self):
        self.assertTrue(m.verify(self.top).ok)

    def test_a_changed_file_is_found(self):
        (self.top / "bin/minidaq_ctl").write_text("client, patched\n")
        r = m.verify(self.top)
        self.assertEqual((r.changed, r.missing, r.added, r.ok), (["bin/minidaq_ctl"], [], [], False))

    def test_a_missing_file_is_found(self):
        (self.top / "debug/minidaq_server.debug").unlink()
        self.assertEqual(m.verify(self.top).missing, ["debug/minidaq_server.debug"])

    def test_an_added_file_is_found(self):
        (self.top / "bin/helper").write_text("x\n")
        self.assertEqual(m.verify(self.top).added, ["bin/helper"])

    def test_a_link_is_reported_as_added(self):
        os.symlink("/etc/hostname", self.top / "bin/link")
        self.assertEqual(m.verify(self.top).added, ["bin/link"])

    def test_every_difference_is_reported_not_only_the_first(self):
        (self.top / "bin/minidaq_ctl").write_text("patched\n")
        (self.top / "bin/minidaq_server").write_text("patched\n")
        (self.top / "BUILDINFO.json").unlink()
        (self.top / "extra").write_text("x\n")
        r = m.verify(self.top)
        self.assertEqual(r.changed, ["bin/minidaq_ctl", "bin/minidaq_server"])
        self.assertEqual(r.missing, ["BUILDINFO.json"])
        self.assertEqual(r.added, ["extra"])

    def test_malformed_manifests_are_refused(self):
        digest = "0" * 64
        for text in ["not a manifest\n", f"{digest} one-space\n", f"{digest[:-1]}  short\n",
                     f"{digest}  ../outside\n", f"{digest}  /etc/passwd\n", f"{digest}  a\n{digest}  a\n"]:
            with self.subTest(text=text):
                (self.top / m.NAME).write_text(text)
                with self.assertRaises(ValueError):
                    m.read_manifest(self.top / m.NAME)


if __name__ == "__main__":
    unittest.main()
