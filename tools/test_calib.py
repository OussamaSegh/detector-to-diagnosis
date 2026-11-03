#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/calib, the calibration procedure (Chapter 26).

The detector here is synthetic and known exactly: each crystal has a gain and a delay, the SiPM
saturates, and the singles come in pairs from annihilations a microsecond apart, so every pair is
isolated. The tests check the procedure finds the gains and delays, and refuses to write a table
when an acceptance criterion fails (SRS-CAL-007).
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:  # ctest counts exit status 77 as skipped
    print("numpy is not installed: skipped")
    sys.exit(77)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.calib import energy, readout, table, timing  # noqa: E402

N = readout.NUM_CRYSTALS
E_SAT = 1500.0


def detector(seed=1):
    rng = np.random.default_rng(seed)
    gain = np.clip(rng.normal(1.0, 0.1, N), 0.7, 1.3)
    delay = np.round(np.clip(rng.normal(0.0, 400.0, N), -2000, 2000))
    return gain, delay


def acquisition(gain, delay, pairs_per_crystal, seed=2, photofraction=0.7, ctr_sigma_ps=127.0):
    """Words of a synthetic acquisition: each annihilation gives two singles in two random crystals,
    1 us after the previous one. Returns the packed words, sorted by time."""
    rng = np.random.default_rng(seed)
    n = N * pairs_per_crystal // 2
    ci = rng.integers(0, N, n)
    cj = (ci + rng.integers(1, N, n)) % N  # never the same crystal
    t0 = np.arange(n, dtype=np.int64) * 1_000_000 + 10_000
    crystal = np.concatenate((ci, cj))
    noise = rng.normal(0.0, ctr_sigma_ps / np.sqrt(2.0), 2 * n)
    t = np.concatenate((t0, t0)) + delay[crystal] + noise
    full = rng.random(2 * n) < photofraction
    e = np.where(full, rng.normal(511.0, 0.05 * 511.0, 2 * n), rng.uniform(100.0, 340.0, 2 * n))
    code = np.clip(np.round(gain[crystal] * energy.saturate(e, E_SAT) / 0.5), 0, readout.MAX_CODE)
    ticks = np.round(t / readout.TIME_LSB_PS).astype(np.int64)
    order = np.argsort(ticks, kind="stable")
    ticks, crystal, code = ticks[order], crystal[order], code.astype(np.int64)[order]
    w = ((crystal.astype(np.uint64) << np.uint64(readout.TIME_BITS + readout.ENERGY_BITS))
         | (code.astype(np.uint64) << np.uint64(readout.TIME_BITS))
         | (ticks.astype(np.uint64) & np.uint64((1 << readout.TIME_BITS) - 1)))
    return w.astype("<u8")


class Crc(unittest.TestCase):
    def test_matches_the_server(self):
        # REQ: SRS-CAL-007
        # The values of minidaq/tests/unit/test_calibration.cpp, computed there by the server.
        self.assertEqual(table.crc32(np.zeros(N), np.full(N, 0.5), np.zeros(N), np.zeros(N, int)),
                         0x6C696A72)
        i = np.arange(N)
        a, b, q, t = np.full(N, 1.5), np.full(N, 0.55), np.full(N, -1e-5), i % 7 - 3
        self.assertEqual(table.crc32(a, b, q, t), 0x0358327D)
        self.assertEqual(table.crc32_slow(a, b, q, t), 0x0358327D)

    def test_written_values_are_exactly_the_float32_values(self):
        doc = table.build({"id": "X", "version": 1, "scanner_serial": "S",
                           "created_utc": "2026-11-03T08:00:00Z",
                           "valid_until_utc": "2027-02-01T08:00:00Z",
                           "reference_temperature_c": 25.0, "procedure": "P"},
                          np.full(N, 0.1), np.full(N, 0.525), np.full(N, -1.1e-5), np.zeros(N, int))
        back = json.loads(json.dumps(doc))
        for key in ("a_kev", "b_kev", "q_kev"):
            v = np.asarray(back["energy"][key])
            self.assertTrue(np.array_equal(v, v.astype(np.float32).astype(float)), key)


class ServerLimits(unittest.TestCase):
    def test_refuses_what_the_server_refuses(self):
        # REQ: SRS-CAL-007
        # The cases of Calibration.RefusesEachCoefficientOutsideWhatADetectorCanHave.
        cases = [((0, 0.24, 0, 0), "gain"), ((0, 1.01, 0, 0), "gain"),
                 ((float("nan"), 0.5, 0, 0), "finite"), ((101, 0.5, 0, 0), "code 0"),
                 ((0, 0.5, -1.3e-4, 0), "falls"), ((0, 0.5, -1.0e-4, 0), "curvature"),
                 ((0, 0.5, 3.7e-4, 0), "curvature"), ((0, 0.5, 0, 5001), "time offset")]
        accepted = [(100, 0.25, 0, 5000), (-100, 1.0, -0.39 / 2047, -5000),
                    (0, 0.5, 1.49 * 0.5 / 2047, 0), (13.06, 0.742, 1.15 * 0.742 / 2047, 0)]
        rows = [c for c, _ in cases] + accepted
        a, b, q, t = (np.array(v) for v in zip(*rows))
        why = table.server_refusals(a, b, q, t)
        for k, (_, text) in enumerate(cases):
            self.assertIn(text, why[k])
        self.assertEqual(list(why[len(cases):]), [""] * len(accepted))


class Readout(unittest.TestCase):
    def test_unwraps_the_time_counter(self):
        span = (1 << readout.TIME_BITS)
        ticks = np.array([span - 10, span - 1, 5, 20], dtype=np.uint64)
        _, _, t = readout.unpack(ticks)
        self.assertEqual(list(t // readout.TIME_LSB_PS), [span - 10, span - 1, span + 5, span + 20])


class Energy(unittest.TestCase):
    def test_finds_photopeaks_and_curve(self):
        rng = np.random.default_rng(3)
        n = 64
        gain = rng.uniform(0.7, 1.3, n)
        crystal = np.repeat(np.arange(n), 3000)
        full = rng.random(crystal.size) < 0.6
        e = np.where(full, rng.normal(511, 25, crystal.size), rng.uniform(100, 340, crystal.size))
        code = np.clip(np.round(gain[crystal] * energy.saturate(e, E_SAT) / 0.5), 0, 2047)
        centre, _, counts, ok = energy.photopeaks(energy.spectra(crystal, code.astype(int), n))
        self.assertTrue(ok.all())
        found = energy.gains_from_peaks(centre, E_SAT)
        self.assertLess(np.abs(found / gain - 1).max(), 0.01)
        a, b, q, worst = energy.fit_curve(found, E_SAT)
        self.assertLess(worst.max(), 0.005)
        # The curve puts each crystal's photopeak at 511 keV.
        e_peak = energy.apply(centre, np.arange(n), a, b, q)
        self.assertLess(np.abs(e_peak - 511).max(), 2.0)


class Timing(unittest.TestCase):
    def test_solves_delays_and_sets_random_pairs_aside(self):
        rng = np.random.default_rng(4)
        n, m = 500, 40_000
        d_true = rng.normal(0, 400, n)
        ci = rng.integers(0, n, m)
        cj = (ci + rng.integers(1, n, m)) % n
        dt = d_true[ci] - d_true[cj] + rng.normal(0, 127, m)
        randoms = rng.random(m) < 0.1
        dt[randoms] = rng.uniform(-4000, 4000, randoms.sum())
        d, rms, kept, _ = timing.solve(ci, cj, dt, n)
        err = d - (d_true - d_true.mean())
        self.assertLess(err.std(), 15.0)  # 127 ps / sqrt(160 pairs) = 10 ps
        self.assertLess(rms, 140.0)
        # A random is kept only when it falls within 4 sigma of the right value: 13% of them.
        self.assertGreater((~kept & randoms).sum(), 0.8 * randoms.sum())


class Procedure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.gain, cls.delay = detector()

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def run_tool(self, words, *extra):
        path = pathlib.Path(self.dir.name)
        (path / "s.words").write_bytes(words.tobytes())
        out = path / "table.json"
        out.unlink(missing_ok=True)
        r = subprocess.run([sys.executable, "-B", "-m", "tools.calib", str(path / "s.words"),
                            "--out", str(out), "--report", str(path / "report.json"),
                            "--id", "CAL-0002", "--version", "2", "--serial", "MDQ-REF-0001",
                            "--e-sat", str(E_SAT), "--now", "2026-11-03T09:00:00Z", *extra],
                           cwd=ROOT, capture_output=True, text=True, check=False)
        return r, out

    def test_writes_a_table_that_matches_the_detector(self):
        # REQ: SRS-CAL-007
        # 140 photopeak singles per crystal: a few fits come out wide by chance, hence the 15%.
        r, out = self.run_tool(acquisition(self.gain, self.delay, 200),
                               "--min-counts", "50", "--min-pairs", "30",
                               "--max-residual-ps", "160", "--max-sigma-fraction", "0.15")
        self.assertEqual(r.returncode, 0, r.stderr)
        doc, a, b, q, t = table.read(out)
        self.assertEqual(doc["valid_until_utc"], "2027-02-01T09:00:00Z")
        # Each crystal's photopeak, through its curve, lands near 511 keV.
        c511 = self.gain * energy.saturate(511.0, E_SAT) / 0.5
        e = a + c511 * (b + c511 * q)
        self.assertLess(np.abs(e - 511.0).std(), 3.0)
        err = t - (self.delay - self.delay.mean())
        self.assertLess(np.abs(err - err.mean()).max(), 60.0)

    def test_reports_each_failing_crystal_and_writes_nothing(self):
        # REQ: SRS-CAL-007
        r, out = self.run_tool(acquisition(self.gain, self.delay, 60))
        self.assertEqual(r.returncode, 1)
        self.assertFalse(out.exists())
        self.assertIn("photopeak counts, 500 needed", r.stderr)
        self.assertIn("more crystals", r.stderr)
        report = json.loads((pathlib.Path(self.dir.name) / "report.json").read_text())
        self.assertEqual(report["summary"]["failed_crystals"], N)
        self.assertTrue(all(c["failures"] for c in report["crystals"]))

    def test_refuses_a_timing_residual_beyond_its_limit(self):
        # REQ: SRS-CAL-007
        r, out = self.run_tool(acquisition(self.gain, self.delay, 200, ctr_sigma_ps=400.0),
                               "--min-counts", "50", "--min-pairs", "30",
                               "--max-residual-ps", "160")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(out.exists())
        self.assertIn("the timing residual is", r.stderr)

    def test_a_missing_file_is_a_usage_error(self):
        r = subprocess.run([sys.executable, "-B", "-m", "tools.calib", "/nonexistent.words",
                            "--out", "x.json", "--id", "C", "--version", "1", "--serial", "S",
                            "--e-sat", "0"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("calib:", r.stderr)


if __name__ == "__main__":
    unittest.main()
