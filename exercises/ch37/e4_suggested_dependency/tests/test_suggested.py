# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 37.4, with a lock file shaped like analysis/requirements.lock."""
import unittest

import suggested as s

LOCK = """\
# Pinned by pip-compile; do not edit by hand.
numpy==2.5.3 \\
    --hash=sha256:00ff
scipy==1.18.1
Pygments==2.21.0  # via pytest
mypy_extensions==1.2.0
python-dateutil==2.9.0.post0
pydicom==2.4.4
"""
APPROVED = ["numpy", "scipy", "matplotlib", "Pygments", "mypy_extensions", "python-dateutil",
            "pydicom", "pybind11"]


class Suggested(unittest.TestCase):
    def test_a_pin_already_in_the_lock_file(self):
        self.assertEqual(s.check("numpy==2.5.3", LOCK, APPROVED), ["already-locked"])

    def test_names_are_compared_as_the_index_compares_them(self):
        self.assertEqual(s.check("pygments==2.21.0", LOCK, APPROVED), ["already-locked"])
        self.assertEqual(s.check("Mypy-Extensions==1.2.0", LOCK, APPROVED), ["already-locked"])
        self.assertEqual(s.check("python_dateutil==2.9.0.post0", LOCK, APPROVED),
                         ["already-locked"])

    def test_another_version_of_a_locked_package_is_a_conflict(self):
        self.assertEqual(s.check("pydicom==3.0.1", LOCK, APPROVED), ["conflict:2.4.4"])

    def test_an_approved_package_not_yet_locked(self):
        self.assertEqual(s.check("pybind11==3.1.0", LOCK, APPROVED), [])

    def test_a_range_is_not_a_pin(self):
        self.assertEqual(s.check("scipy>=1.18", LOCK, APPROVED), ["unpinned", "conflict:1.18.1"])
        self.assertEqual(s.check("matplotlib", LOCK, APPROVED), ["unpinned"])
        self.assertEqual(s.check("matplotlib==3.*", LOCK, APPROVED), ["unpinned"])

    def test_look_alikes_of_approved_packages(self):
        cases = {"nunpy==1.0": "numpy", "nmupy==1.0": "numpy", "num-py==1.0": "numpy",
                 "py-dicom==1.0": "pydicom", "pydicom2==1.0": "pydicom", "dicom==1.0": "pydicom",
                 "scapy==2.6": "scipy", "matplotlib-==1.0": None, "mathplotlib==1.0": "matplotlib",
                 "dateutil==2.9": "python-dateutil"}
        for line, near in cases.items():
            if near is None:
                with self.assertRaises(ValueError, msg=line):
                    s.check(line, LOCK, APPROVED)
                continue
            got = s.check(line, LOCK, APPROVED)
            self.assertIn("not-approved", got, line)
            self.assertIn(f"near:{near}", got, line)

    def test_an_unrelated_package_is_not_approved_and_near_nothing(self):
        self.assertEqual(s.check("requests==2.32.3", LOCK, APPROVED), ["not-approved"])
        self.assertEqual(s.check("pandas==3.0.0", LOCK, APPROVED), ["not-approved"])

    def test_lines_that_are_not_requirements_are_refused(self):
        for bad in ("", "numpy==", "==1.0", "numpy 2.5.3", "numpy==2.5.3; rm -rf /",
                    "git+https://example.invalid/numpy.git"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                s.check(bad, LOCK, APPROVED)


if __name__ == "__main__":
    unittest.main()
