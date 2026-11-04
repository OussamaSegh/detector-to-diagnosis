#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/lock_audit.py with a fake index, so that they need no network."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lock_audit

LOCK = """# a comment
numpy==2.5.3
pillow==12.3.0  # with a comment
Pygments==2.21.0 \\
    --hash=sha256:0
not-pinned>=1
"""

RECORDS = {
    ("numpy", "2.5.3"): {"vulnerabilities": []},
    ("pillow", "12.3.0"): {"vulnerabilities": [{"id": "GHSA-1", "fixed_in": ["13.0.0"]},
                                               {"id": "PYSEC-2", "fixed_in": []}]},
    ("Pygments", "2.21.0"): {"vulnerabilities": []},
}


def fake(name, version):
    return RECORDS[(name, version)]


class LockAudit(unittest.TestCase):
    def test_every_exact_pin_is_read_and_nothing_else(self):
        self.assertEqual(lock_audit.pins(LOCK),
                         [("numpy", "2.5.3"), ("pillow", "12.3.0"), ("Pygments", "2.21.0")])

    def test_a_pinned_version_with_an_advisory_is_reported_with_its_fix(self):
        found = lock_audit.audit(LOCK, fake)
        self.assertEqual(found["numpy==2.5.3"], [])
        self.assertEqual(found["pillow==12.3.0"], [("GHSA-1", "13.0.0"), ("PYSEC-2", "no fix")])

    def test_a_record_without_the_field_is_an_error_not_a_clean_result(self):
        with self.assertRaises(RuntimeError):
            lock_audit.audit("numpy==2.5.3\n", lambda n, v: {"info": {}})


if __name__ == "__main__":
    unittest.main()
