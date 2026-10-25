# SPDX-License-Identifier: MIT
import math
import unittest

import budget as b

# The chapter's measurements (measurements/ch11): the NEMA-style phantom in
# MiniDAQ's ring gives 0.167 singles per decay; without dead time the prompts
# are 1.346e-3 per Bq of trues and scatters plus 6.6e-12 per Bq^2 of randoms;
# the sorter's pair stage is full at about 68 M singles/s on the book's VM.
SINGLES_PER_BQ = 0.167
PAIR_CAPACITY = 68e6
COINCIDENCE_BYTES = 16     # an assumed list-mode record size
DISK_BYTES_PER_S = 200e6   # one SATA SSD, sustained (assumption)
WRITER_CAPACITY = 5e6      # coincidences/s the writer formats (assumption)


def singles(a):
    return SINGLES_PER_BQ * a


def prompts(a):
    return 1.346e-3 * a + 6.6e-12 * a * a


def chain(link_bits_per_s):
    return [
        b.Stage("link", singles, b.link_singles_capacity(link_bits_per_s, 182)),
        b.Stage("sorter", singles, PAIR_CAPACITY),
        b.Stage("writer", prompts, WRITER_CAPACITY),
        b.Stage("disk", lambda a: prompts(a) * COINCIDENCE_BYTES, DISK_BYTES_PER_S),
    ]


class Budget(unittest.TestCase):
    def test_link_capacity_matches_chapter_9(self):
        self.assertAlmostEqual(b.link_singles_capacity(1e9, 182) / 1e6, 14.79, places=2)
        self.assertAlmostEqual(b.link_singles_capacity(10e9, 182) / 1e6, 147.9, places=1)
        self.assertAlmostEqual(b.link_singles_capacity(1e9, 182, links=4), 4 * b.link_singles_capacity(1e9, 182))

    def test_saturation_by_hand(self):
        stage = b.Stage("x", lambda a: 2.0 * a, 100.0)
        self.assertAlmostEqual(b.saturation_activity(stage), 50.0, places=6)
        self.assertAlmostEqual(b.saturation_activity(stage, margin=0.2), 40.0, places=6)
        self.assertAlmostEqual(b.utilization(stage, 25.0), 0.5)
        self.assertTrue(math.isinf(b.saturation_activity(b.Stage("never", lambda a: 0.0, 1.0))))

    def test_gigabit_link_saturates_first(self):
        # The writer has the smallest capacity, 5 M, but it counts coincidences,
        # of which there are about fifty times fewer than singles.
        name, a = b.first_bottleneck(chain(1e9))
        self.assertEqual(name, "link")
        self.assertAlmostEqual(a / 1e6, 88.6, delta=0.1)

    def test_with_10_gbe_the_sorter_saturates_first(self):
        name, a = b.first_bottleneck(chain(10e9))
        self.assertEqual(name, "sorter")
        self.assertAlmostEqual(a / 1e6, 407.2, delta=0.1)
        name, a = b.first_bottleneck(chain(10e9), margin=0.3)
        self.assertEqual(name, "sorter")
        self.assertAlmostEqual(a / 1e6, 285.0, delta=0.1)

    def test_the_disk_is_quadratic(self):
        disk = chain(10e9)[2]
        # The randoms term makes the disk fill faster than linearly.
        self.assertGreater(b.utilization(disk, 400e6) / b.utilization(disk, 200e6), 2.0)


if __name__ == "__main__":
    unittest.main()
