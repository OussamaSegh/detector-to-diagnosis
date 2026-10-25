# SPDX-License-Identifier: MIT
import math
import os
import struct
import unittest
import zlib

import sino2d as s

HERE = os.path.dirname(os.path.abspath(__file__))
# 0.1 s of a 1 MBq point source at (40, -25, 0) mm in air, written by
# minidaq_sim --listmode; the expected sinogram is what minidaq_listmode sino made of it.
FILE = os.path.join(HERE, "point_source.mdql")


class LorBin(unittest.TestCase):
    def test_known_lors(self):
        self.assertEqual(s.lor_bin(0, 192), (96, 0))     # a diameter
        self.assertEqual(s.lor_bin(192, 0), (96, 0))     # either order
        self.assertIsNone(s.lor_bin(7, 7))
        # k = 584 is past 180 degrees: k becomes 200, d = 183 becomes 384 - 183 = 201.
        self.assertEqual(s.lor_bin(200, 383), (100, 9))

    def test_every_lor_has_its_own_bin(self):
        seen = set()
        for i in range(s.N):
            for j in range(i + 1, s.N):
                v, r = s.lor_bin(i, j)
                self.assertTrue(0 <= v < s.VIEWS and -191 <= r <= 191, (i, j, v, r))
                seen.add((v, r))
        self.assertEqual(len(seen), s.N * (s.N - 1) // 2, "two LORs share a bin")

    def test_radial_position_is_the_distance_of_the_lor(self):
        for i, j in [(0, 100), (10, 300), (200, 383), (5, 6), (100, 290)]:
            v, r = s.lor_bin(i, j)
            th = ((i + j + 1) % s.N) * math.pi / s.N
            a = (i + 0.5) * 2 * math.pi / s.N
            x, y = s.RADIUS_MM * math.cos(a), s.RADIUS_MM * math.sin(a)
            self.assertAlmostEqual(s.radial_position_mm(r), x * math.cos(th) + y * math.sin(th), places=9)


class Sinogram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coinc = s.read_coincidences(FILE)
        cls.sino = s.sinogram(cls.coinc)

    def test_only_prompts_are_counted(self):
        prompts = sum(1 for c in self.coinc if not c[3])
        self.assertEqual(prompts, 6155)
        self.assertEqual(sum(map(sum, self.sino)), prompts)

    def test_same_sinogram_as_minidaq(self):
        raw = zlib.decompress(open(os.path.join(HERE, "expected_prompts2d.u32.z"), "rb").read())
        expected = struct.unpack(f"<{len(raw) // 4}I", raw)
        width = len(self.sino[0])
        self.assertEqual(width, 227)
        for v in range(s.VIEWS):
            self.assertEqual(self.sino[v], list(expected[v * width : (v + 1) * width]), f"view {v}")

    def test_the_sinusoid_gives_back_the_source(self):
        # About 3.6 % short of (40, -25): the README's "Then, by hand" asks why.
        x, y = s.fit_point(self.sino)
        self.assertAlmostEqual(x, 40.0, delta=2.5)
        self.assertAlmostEqual(y, -25.0, delta=2.5)
        self.assertLess(math.hypot(x, y), math.hypot(40, -25), "the fitted point is inside the true one")


if __name__ == "__main__":
    unittest.main()
