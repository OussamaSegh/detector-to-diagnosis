#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/release_bundle.py (Chapter 20): packaging is deterministic, and verification
finds each kind of damage it claims to find. The programs are two small ones compiled here with
debug information, so the test needs a C++ compiler and binutils, not a MiniDAQ build.

    test_release_bundle.py [CXX]
"""
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_bundle as rb  # noqa: E402

CXX = sys.argv.pop(1) if len(sys.argv) > 1 else "g++"
INFO = {"product": "MiniDAQ", "version": "9.9.9", "commit": "0123456789abcdef0123456789abcdef01234567",
        "source_date_epoch": 1761400000}


def fake_sbom(path):
    path.write_text('{"bomFormat": "CycloneDX"}\n')


class Bundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.programs = []
        for name, text in [("minidaq_server", "server"), ("minidaq_ctl", "client")]:
            src = cls.tmp / f"{name}.cpp"
            src.write_text(f'#include <cstdio>\nint main() {{ std::puts("{text}"); }}\n')
            subprocess.run([CXX, "-O2", "-g", "-Wl,--build-id", str(src), "-o", str(cls.tmp / name)], check=True)
            cls.programs.append(cls.tmp / name)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def setUp(self):
        self.out = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        self.product = rb.package_product(self.programs, INFO, self.out, fake_sbom)

    def verify(self, product=None, evidence=None):
        argv = ["verify", str(product or self.product)] + (["--evidence", str(evidence)] if evidence else [])
        with open(os.devnull, "w") as null:
            stdout, sys.stdout = sys.stdout, null
            try:
                return rb.main(argv)
            finally:
                sys.stdout = stdout

    def rewrite(self, change):
        """A copy of the product archive with `change(top)` applied to its unpacked files."""
        work = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        top = rb.unpack(self.product, work / "x")
        change(top)
        files = sorted(str(p.relative_to(top)) for p in top.rglob("*") if p.is_file())
        damaged = work / self.product.name
        rb.write_tar(damaged, top, files)
        return damaged

    def evidence_dir(self, **files):
        d = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        content = {
            "commit.txt": f"commit {INFO['commit']}\n",
            "release-checks.txt": "pass  static analysis\nall release checks passed\n",
            "system-test-report.md": "| Software | MiniDAQ 9.9.9 |\n\nThe system tests passed.\n",
            "run_all.txt": "=== all gates passed ===\n",
        }
        content.update(files)
        for name, text in content.items():
            if text is not None:
                (d / name).write_text(text)
        return d

    def test_a_fresh_product_verifies(self):
        self.assertEqual(self.verify(), 0)

    def test_the_programs_are_listed_as_recorded(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(rb.main(["programs", str(self.product)]), 0)
        lines = out.getvalue().splitlines()
        self.assertEqual([line.split()[0] for line in lines], ["minidaq_server", "minidaq_ctl"])
        for line, program in zip(lines, self.programs):
            self.assertIn(f"build ID {rb.build_id(program)}", line)

    def test_packaging_twice_gives_the_same_bytes(self):
        again = rb.package_product(self.programs, INFO, pathlib.Path(tempfile.mkdtemp(dir=self.tmp)), fake_sbom)
        self.assertEqual(rb.sha256(again), rb.sha256(self.product))

    def test_the_archive_holds_no_time_and_no_owner(self):
        with tarfile.open(self.product) as tar:
            for m in tar.getmembers():
                self.assertEqual((m.mtime, m.uid, m.gid, m.uname, m.gname), (INFO["source_date_epoch"], 0, 0, "", ""))

    def test_the_shipped_program_runs_without_its_debug_information(self):
        work = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        top = rb.unpack(self.product, work)
        out = subprocess.run([str(top / "bin/minidaq_ctl")], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out, "client\n")
        self.assertNotIn(".debug_info", rb.run("readelf", "-S", "-W", str(top / "bin/minidaq_ctl")))
        self.assertIn(".debug_info", rb.run("readelf", "-S", "-W", str(top / "debug/minidaq_ctl.debug")))

    def test_a_changed_byte_is_found(self):
        def flip(top):
            data = bytearray((top / "bin/minidaq_server").read_bytes())
            data[-1] ^= 1
            (top / "bin/minidaq_server").write_bytes(bytes(data))
        self.assertEqual(self.verify(self.rewrite(flip)), 1)

    def test_an_added_file_is_found(self):
        self.assertEqual(self.verify(self.rewrite(lambda top: (top / "bin/extra").write_text("x"))), 1)

    def test_a_missing_file_is_found(self):
        self.assertEqual(self.verify(self.rewrite(lambda top: (top / "sbom/minidaq.cdx.json").unlink())), 1)

    def test_swapped_debug_files_are_found_even_with_a_matching_manifest(self):
        def swap(top):
            a, b = top / "debug/minidaq_server.debug", top / "debug/minidaq_ctl.debug"
            data = a.read_bytes()
            a.write_bytes(b.read_bytes())
            b.write_bytes(data)
            rb.write_manifest(top)  # someone "repaired" the manifest
        self.assertEqual(self.verify(self.rewrite(swap)), 1)

    def test_matching_evidence_verifies(self):
        evidence = rb.package_evidence(self.product, self.evidence_dir(), self.out)
        self.assertEqual(self.verify(evidence=evidence), 0)

    def test_evidence_of_another_product_is_refused(self):
        other = rb.package_product(self.programs[:1], INFO, pathlib.Path(tempfile.mkdtemp(dir=self.tmp)), fake_sbom)
        evidence = rb.package_evidence(other, self.evidence_dir(), self.out)
        self.assertEqual(self.verify(evidence=evidence), 1)

    def test_evidence_of_a_dirty_tree_is_refused(self):
        d = self.evidence_dir(**{"commit.txt": f"commit {INFO['commit']}\n M minidaq/src/x.cpp\n"})
        self.assertEqual(self.verify(evidence=rb.package_evidence(self.product, d, self.out)), 1)

    def test_evidence_of_a_failed_check_is_refused(self):
        d = self.evidence_dir(**{"release-checks.txt": "FAIL  soak, 30 minutes at 1 M singles/s\n"})
        self.assertEqual(self.verify(evidence=rb.package_evidence(self.product, d, self.out)), 1)

    def test_evidence_without_a_system_test_report_is_refused(self):
        d = self.evidence_dir(**{"system-test-report.md": None})
        self.assertEqual(self.verify(evidence=rb.package_evidence(self.product, d, self.out)), 1)


if __name__ == "__main__":
    unittest.main()
