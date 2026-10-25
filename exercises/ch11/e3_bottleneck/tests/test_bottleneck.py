# SPDX-License-Identifier: MIT
import unittest

import bottleneck as b

# A real report: 50 MBq of the NEMA-style source replayed for 1 s.
SAMPLE = """\
rate 8.36e+06 words/s, 1 s, batch 4096, delivered 8389315, dropped 0, behind schedule 2830
stage          batches       p50       p99     p99.9    p99.99        max   (microseconds)
source            2050     258.0     327.7    1187.8    1934.4     1934.4
decode            2050      12.4      26.9      46.3     189.2      189.2
sort              2050      38.9      65.5     100.9    1277.3     1277.3
pair              2050      43.3      80.9      94.7     492.8      492.8
write             2050       0.1       0.1       0.1       0.6        0.6
end-to-end        2050     761.9    2089.0    4177.9    4586.4     4586.4
stage            items in  busy %   out stalls      in idle      dropped
source            8389315    53.6            0            0            0
decode            8389315     2.7            0       173873            0
sort              8389315     8.3            0       171907            0
pair              8389315     9.7            0       171418            0
write              135962     0.0            0       174156            0
sorter: 8389315 singles, 5329155 energy rejected, 0 out of order, 103284 prompts, 32678 delayed
"""

# measurements/ch11/bottleneck.txt: singles/s, dropped %, busy % of source,
# decode, sort, pair, write.
SWEEP = [
    (3.34e6, 0.00, 23.2, 1.6, 3.7, 4.2, 0.0), (3.34e6, 0.00, 22.9, 1.4, 3.5, 4.0, 0.0),
    (8.35e6, 0.00, 57.4, 3.8, 10.0, 11.1, 0.0), (8.35e6, 0.00, 53.4, 3.6, 9.8, 10.8, 0.0),
    (1.67e7, 0.00, 63.8, 6.8, 19.6, 23.0, 0.1), (1.67e7, 0.00, 63.5, 6.7, 19.1, 22.9, 0.0),
    (3.34e7, 0.00, 64.1, 10.8, 36.6, 45.7, 0.0), (3.34e7, 0.00, 64.6, 11.0, 35.5, 45.3, 0.0),
    (5.01e7, 0.00, 65.0, 15.4, 50.9, 70.2, 0.1), (5.01e7, 0.00, 65.3, 15.1, 53.4, 72.9, 0.1),
    (6.68e7, 0.06, 65.6, 19.8, 68.1, 97.5, 0.1), (6.68e7, 0.17, 65.7, 19.0, 69.0, 97.3, 0.1),
]
STAGES = ["source", "decode", "sort", "pair", "write"]


def report_text(rate, dropped_pct, *busy):
    """A minimal report with the numbers of one sweep row (3 s at `rate`)."""
    offered = round(rate * 3)
    dropped = round(offered * dropped_pct / 100)
    lines = [f"rate {rate:.3g} words/s, 3 s, batch 4096, delivered {offered - dropped}, dropped {dropped}, "
             "behind schedule 0",
             "stage            items in  busy %   out stalls      in idle      dropped"]
    lines += [f"{s:<12} {offered - dropped:>12} {u:>7.1f} {0:>12} {0:>12} {0:>12}" for s, u in zip(STAGES, busy)]
    return "\n".join(lines) + "\n"


def sweep():
    return [b.parse_report(report_text(*row)) for row in SWEEP]


class Bottleneck(unittest.TestCase):
    def test_parse_the_sample(self):
        r = b.parse_report(SAMPLE)
        self.assertEqual(r.rate, 8.36e6)
        self.assertEqual((r.delivered, r.dropped), (8389315, 0))
        self.assertEqual(list(r.stages), STAGES, "the latency table and end-to-end are not stages")
        self.assertEqual(r.stages["pair"], b.StageUse(8389315, 9.7, 0, 171418, 0))
        self.assertEqual(r.stages["write"].items_in, 135962)

    def test_not_a_report(self):
        with self.assertRaises(ValueError):
            b.parse_report("hello\n")

    def test_the_source_is_not_a_limit(self):
        # The replay source is 53.6% busy, but the pair stage is the busiest
        # stage that can limit the pipeline, and it has headroom.
        r = b.parse_report(SAMPLE)
        self.assertEqual(b.busiest(r), ("pair", 9.7))
        self.assertIsNone(b.saturated(r))

    def test_saturated_at_400_mbq(self):
        reports = sweep()
        self.assertEqual(b.saturated(reports[-1]), "pair")
        # At 300 MBq the pair stage is 73% busy and nothing is dropped.
        self.assertIsNone(b.saturated(reports[-3]))
        # Drops make the busiest stage saturated even below the busy limit.
        self.assertEqual(b.saturated(reports[-1], busy_limit=99.0), "pair")

    def test_capacity_from_the_whole_sweep(self):
        reports = sweep()
        self.assertAlmostEqual(b.capacity(reports, "pair") / 1e6, 69.82, delta=0.05)
        self.assertAlmostEqual(b.capacity(reports, "sort") / 1e6, 95.85, delta=0.05)
        name, cap = b.first_bottleneck(reports)
        self.assertEqual(name, "pair")
        self.assertAlmostEqual(cap / 1e6, 69.82, delta=0.05)


if __name__ == "__main__":
    unittest.main()
