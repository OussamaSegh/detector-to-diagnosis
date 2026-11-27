# SPDX-License-Identifier: MIT
"""Exercise 8.6 (A): tests of the agent's find_pairs, from the specification and the physics."""
import random
import unittest


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def S(self, *a):
        return self.subject.Single(*a)

    def test_two_singles_in_one_window_are_one_pair(self):
        a, b = self.S(0, 1, 511.0), self.S(1_000, 2, 511.0)
        self.assertEqual(self.subject.find_pairs([a, b], 4_000), [(a, b)])

    def test_singles_exactly_one_window_apart_are_a_pair_and_one_more_are_not(self):
        a = self.S(0, 1, 511.0)
        self.assertEqual(len(self.subject.find_pairs([a, self.S(4_000, 2, 511.0)], 4_000)), 1)
        self.assertEqual(self.subject.find_pairs([a, self.S(4_001, 2, 511.0)], 4_000), [])

    def test_two_singles_of_one_crystal_are_no_pair(self):
        self.assertEqual(self.subject.find_pairs([self.S(0, 7, 511.0), self.S(10, 7, 480.0)], 4_000), [])

    def test_n_separated_annihilations_give_n_pairs(self):
        # Each decay gives two back-to-back photons in two crystals; decays 1 us apart.
        singles = [self.S(k * 1_000_000 + dt, c, 511.0)
                   for k in range(100) for dt, c in ((0, k % 50), (300, 50 + k % 50))]
        self.assertEqual(len(self.subject.find_pairs(singles, 4_000)), 100)

    def test_three_singles_in_one_window_are_three_pairs_each_once(self):
        a, b, c = self.S(0, 1, 511.0), self.S(1_000, 2, 511.0), self.S(2_000, 3, 511.0)
        pairs = self.subject.find_pairs([a, b, c], 4_000)
        self.assertEqual(sorted(pairs), sorted([(a, b), (a, c), (b, c)]))

    def test_chance_pairs_of_independent_detectors_match_two_tau_s1_s2(self):
        # Exercise 8.3: R = 2 tau S1 S2. Two detectors (crystals 1 and 2) at 1 M singles/s each
        # for 0.25 s, tau = 4 ns: 2,000 chance pairs expected, standard deviation about 45.
        rng = random.Random(8)
        singles = []
        for crystal in (1, 2):
            t = 0.0
            while (t := t + rng.expovariate(1e6)) < 0.25:
                singles.append(self.S(round(t * 1e12), crystal, 511.0))
        expected = self.subject.expected_randoms_per_s(1e6, 1e6, 4e-9) * 0.25
        n = len(self.subject.find_pairs(singles, 4_000))
        self.assertLess(abs(n - expected), 4 * expected ** 0.5, f"{n} pairs, {expected:.0f} expected")

    def test_the_result_does_not_depend_on_the_order_of_singles_with_equal_times(self):
        singles = [self.S(0, 9, 470.0), self.S(0, 3, 520.0), self.S(0, 5, 500.0),
                   self.S(500, 12, 511.0), self.S(500, 12, 450.0)]
        want = self.subject.find_pairs(singles, 4_000)
        rng = random.Random(27)
        for _ in range(20):
            rng.shuffle(singles)
            self.assertEqual(self.subject.find_pairs(singles, 4_000), want)

    def test_a_pair_with_equal_times_starts_with_the_lower_crystal(self):
        a, b = self.S(100, 4, 511.0), self.S(100, 2, 511.0)
        self.assertEqual(self.subject.find_pairs([a, b], 4_000), [(b, a)])
