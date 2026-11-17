# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 40.4. The advisories are made up; the version rules are real."""
import unittest

import affected as a

# An advisory of the project: introduced in 1.1.1, fixed in 1.1.1t; introduced in 3.0.0, fixed in
# 3.0.14.
RANGES = [("1.1.1", "1.1.1t"), ("3.0.0", "3.0.14")]


class OpenSSL(unittest.TestCase):
    def test_letters_order_patch_releases(self):
        order = ["1.0.2zh", "1.1.1", "1.1.1a", "1.1.1s", "1.1.1t", "1.1.1w", "1.1.1z", "1.1.1za",
                 "3.0.0", "3.0.9", "3.0.13", "3.0.14"]
        keys = [a.openssl_key(v) for v in order]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))

    def test_upstream_ranges(self):
        for v, want in (("1.0.2zh", False), ("1.1.1", True), ("1.1.1s", True), ("1.1.1t", False),
                        ("1.1.1w", False), ("3.0.0", True), ("3.0.13", True), ("3.0.14", False)):
            self.assertEqual(a.upstream_affected(v, RANGES), want, v)
        self.assertTrue(a.upstream_affected("3.5.1", [("3.5.0", None)]))

    def test_versions_that_are_not_openssl_versions_are_refused(self):
        for bad in ("3.0", "3.0.13-0ubuntu3.5", "1.1.1W", "v3.0.13", ""):
            with self.assertRaises(ValueError, msg=bad):
                a.openssl_key(bad)


class Debian(unittest.TestCase):
    def test_dpkg_order(self):
        pairs = [("3.0.13-0ubuntu3.4", "3.0.13-0ubuntu3.5"),
                 ("3.0.13-0ubuntu3.5", "3.0.13-0ubuntu3.16"),
                 ("3.0.2-0ubuntu1.9", "3.0.2-0ubuntu1.10"),
                 ("3.0.13~rc1-1", "3.0.13-1"), ("2.0-1", "1:1.0-1"), ("1.0-1", "1.0-1ubuntu1"),
                 ("1.0a-1", "1.0+b1-1"), ("3.0.13", "3.0.13-0ubuntu1")]
        for older, newer in pairs:
            self.assertEqual(a.debian_compare(older, newer), -1, (older, newer))
            self.assertEqual(a.debian_compare(newer, older), 1, (newer, older))
        self.assertEqual(a.debian_compare("1:3.0.13-0ubuntu3.5", "1:3.0.13-0ubuntu3.5"), 0)
        self.assertEqual(a.upstream_of("1:3.0.13-0ubuntu3.5"), "3.0.13")


class Verdict(unittest.TestCase):
    SHIPPED = "3.0.13-0ubuntu3.5"

    def test_the_distribution_decides_when_it_has_spoken(self):
        self.assertEqual(a.verdict(self.SHIPPED, RANGES, distro_fixed="3.0.13-0ubuntu3.4"),
                         "not-affected")
        self.assertEqual(a.verdict("3.0.13-0ubuntu3.1", RANGES, distro_fixed="3.0.13-0ubuntu3.4"),
                         "affected")
        self.assertEqual(a.verdict(self.SHIPPED, RANGES, distro_fixed="not-affected"),
                         "not-affected")

    def test_without_it_the_upstream_range_is_only_a_lead(self):
        self.assertEqual(a.verdict(self.SHIPPED, RANGES), "affected-upstream")
        self.assertEqual(a.verdict("3.0.14-1", RANGES), "not-affected-upstream")


if __name__ == "__main__":
    unittest.main()
