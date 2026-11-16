# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 39.3."""
import math
import random
import unittest

from calibrate import block_offsets

C = 0.299792458
R = 156.0
BLOCKS = 8
TRUTH = [0.0, 120.0, -80.0, 40.0, 0.0, 300.0, -150.0, 60.0]


def block_of(point):
    angle = math.atan2(point[1], point[0]) % (2 * math.pi)
    return int(angle / (2 * math.pi / BLOCKS)) % BLOCKS


def events(source, n=40_000, offsets=TRUTH, ctr=300.0, seed=39, skip=None):
    """n coincidences of a point source: a line in a random direction through it, the two
    crystals where it meets the ring, each single stamped by its block's clock with timing noise
    (the pair's noise has a FWHM of ctr)."""
    rng = random.Random(seed)
    sigma_single = ctr / 2.3548200450309493 / math.sqrt(2.0)
    out = []
    while len(out) < n:
        theta = rng.uniform(0, math.pi)
        d = (math.cos(theta), math.sin(theta))
        pd = source[0] * d[0] + source[1] * d[1]
        root = math.sqrt(pd * pd - (source[0] ** 2 + source[1] ** 2 - R * R))
        a = (source[0] + (-pd - root) * d[0], source[1] + (-pd - root) * d[1])
        b = (source[0] + (-pd + root) * d[0], source[1] + (-pd + root) * d[1])
        ba, bb = block_of(a), block_of(b)
        if skip is not None and skip in (ba, bb):
            continue
        t0 = rng.uniform(0, 1e9)
        ta = t0 + math.dist(source, a) / C + offsets[ba] + rng.gauss(0, sigma_single)
        tb = t0 + math.dist(source, b) / C + offsets[bb] + rng.gauss(0, sigma_single)
        out.append((a, b, ba, bb, ta, tb))
    return out


def centered(values, seen):
    m = sum(values[k] for k in seen) / len(seen)
    return [values[k] - m if k in seen else None for k in range(len(values))]


class Offsets(unittest.TestCase):
    def check(self, got, truth, seen):
        want = centered(truth, seen)
        for k in range(BLOCKS):
            if k in seen:
                self.assertAlmostEqual(got[k], want[k], delta=8.0, msg=f"block {k}")
            else:
                self.assertIsNone(got[k], f"block {k}")

    def test_a_source_at_the_center_cannot_tell(self):
        # Every line through the center joins a block to the one opposite: four pairs of blocks
        # and nothing between them. An answer would be made up.
        with self.assertRaises(ValueError):
            block_offsets(events((0.0, 0.0), n=4000), (0.0, 0.0), BLOCKS)

    def test_a_source_off_center(self):
        s = (60.0, -25.0)
        self.check(block_offsets(events(s), s, BLOCKS), TRUTH, set(range(8)))

    def test_a_block_that_saw_nothing(self):
        s = (30.0, 10.0)
        got = block_offsets(events(s, skip=3), s, BLOCKS)
        self.check(got, TRUTH, set(range(8)) - {3})
        self.assertAlmostEqual(sum(g for g in got if g is not None), 0.0, delta=1e-6)

    def test_either_crystal_can_be_a(self):
        s = (30.0, 10.0)
        ev = events(s, n=5000)
        swapped = [(b, a, bb, ba, tb, ta) for a, b, ba, bb, ta, tb in ev]
        one, other = block_offsets(ev, s, BLOCKS), block_offsets(swapped, s, BLOCKS)
        for x, y in zip(one, other):
            self.assertAlmostEqual(x, y, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
