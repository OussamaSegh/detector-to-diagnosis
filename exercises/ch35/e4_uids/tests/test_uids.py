# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 35.4."""
import itertools
import unittest

import uids as u

STUDY = "2.25.329800735698586629295641978511506172918"


class Valid(unittest.TestCase):
    def test_valid_uids(self):
        for good in ("1.2.840.10008.1.2.1", "0.0", "2", STUDY, "2.25." + "9" * 39,
                     "1." * 31 + "11"):
            self.assertTrue(u.valid(good), good)

    def test_invalid_uids(self):
        for bad in ("", "1..2", "1.2.", ".1", "1.02", "01.2", "1.2.a", "1.2 ", " 1.2", "1.2\n",
                    "1.2\x00", "1." * 32 + "1", None, 1.2, b"1.2"):
            self.assertFalse(u.valid(bad), repr(bad))


class FromUuid(unittest.TestCase):
    def test_the_example_of_x667(self):
        self.assertEqual(u.from_uuid("f81d4fae-7dec-11d0-a765-00a0c91e6bf6"),
                         "2.25.329800735698586629295641978511506172918")

    def test_a_uuid_with_leading_zero_bits_is_still_valid(self):
        self.assertEqual(u.from_uuid("00000000-0000-0000-0000-00000000000a"), "2.25.10")
        self.assertTrue(u.valid(u.from_uuid("00000000-0000-0000-0000-00000000000a")))


class Derived(unittest.TestCase):
    def test_the_same_parts_give_the_same_valid_uid(self):
        a = u.derived("series", STUDY, "ab12" * 16)
        self.assertEqual(a, u.derived("series", STUDY, "ab12" * 16))
        self.assertTrue(u.valid(a) and a.startswith("2.25.") and len(a) <= 44, a)

    def test_different_parts_never_give_the_same_text(self):
        lists = [("1.2", "3"), ("1", "2.3"), ("a", "b"), ("ab",), ("a", "", "b"), ("a\x1fb",),
                 ("a", "b", ""), ("1",), (1,), ("instance", STUDY, 1), ("instance", STUDY + ".1"),
                 ("s1:a",), ("a", "s1:")]
        seen = {}
        for parts in lists:
            got = u.derived(*parts)
            self.assertNotIn(got, seen, f"{parts} and {seen.get(got)}")
            seen[got] = parts

    def test_every_slice_of_a_series_has_its_own_uid(self):
        series = u.derived("series", STUDY, "0" * 64)
        got = {u.derived("instance", series, k) for k in range(500)}
        self.assertEqual(len(got), 500)
        self.assertTrue(all(u.valid(g) for g in got))

    def test_parts_whose_text_is_not_exact_are_refused(self):
        for bad in (1.5, None, b"x", True, ("a",)):
            with self.assertRaises(TypeError, msg=repr(bad)):
                u.derived("series", bad)
        with self.assertRaises(ValueError):
            u.derived()

    def test_no_pair_of_short_lists_collides(self):
        alphabet = ["", "1", ".", "1.", ".1", "11", "a", "a1"]
        got = {}
        for n in (1, 2, 3):
            for parts in itertools.product(alphabet, repeat=n):
                d = u.derived(*parts)
                self.assertNotIn(d, got, f"{parts} and {got.get(d)}")
                got[d] = parts


if __name__ == "__main__":
    unittest.main()
