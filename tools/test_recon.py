#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/recon, the corrections of Chapter 27 (tool TL-30).

Synthetic data with known answers for each correction, and, when the directory of MiniDAQ's
programs is given, one simulated run end to end: the list-mode reader and the bin of every
coincidence must agree exactly with minidaq_listmode sino.

    test_recon.py [DIR_OF_MINIDAQ_SIM_AND_MINIDAQ_LISTMODE]
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zlib

try:
    import numpy as np
except ImportError:  # ctest counts exit status 77 as skipped
    print("numpy is not installed: skipped")
    sys.exit(77)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.recon import corrections as cor, listmode, mlem, project, sinogram as sg  # noqa: E402

BIN_DIR = None
N = sg.CRYSTALS_PER_RING


def header(fov=120.0, mrd=47):
    r_max = int(np.floor(np.arcsin(min(fov / sg.RADIUS_MM, 1.0)) * N / np.pi))
    return sg.Header(path=pathlib.Path("x.hdr"), radial_bins=2 * r_max + 1, views=N // 2,
                     slices=95, tof_bins=1, first_r=-r_max, max_ring_difference=mrd,
                     fov_radius_mm=fov, files={})


class Geometry(unittest.TestCase):
    def test_each_bin_holds_one_transaxial_pair(self):
        h = header(fov=149.0)
        ti, tj = sg.crystal_pairs(h)
        self.assertTrue((ti >= 0).all())
        self.assertTrue((ti < tj).all())
        pairs = set(zip(ti.ravel().tolist(), tj.ravel().tolist()))
        self.assertEqual(len(pairs), ti.size)

    def test_a_bins_line_is_where_its_coordinates_say(self):
        h = header()
        ti, tj = sg.crystal_pairs(h)
        ang = lambda t: (t + 0.5) * 2 * np.pi / N  # noqa: E731
        xa, ya = sg.RADIUS_MM * np.cos(ang(ti)), sg.RADIUS_MM * np.sin(ang(ti))
        xb, yb = sg.RADIUS_MM * np.cos(ang(tj)), sg.RADIUS_MM * np.sin(ang(tj))
        # Distance of the line from the axis, and its normal's angle modulo pi.
        dist = np.abs(xa * yb - xb * ya) / np.hypot(xb - xa, yb - ya)
        self.assertLess(np.abs(dist - np.abs(h.s_mm)[None, :]).max(), 1e-9)
        normal = np.mod(np.arctan2(ya + yb, xa + xb), np.pi)
        diff = np.abs(np.mod(normal - h.phi[:, None] + np.pi / 2, np.pi) - np.pi / 2)
        off_axis = np.abs(h.s_mm) > 1.0  # a line through the axis has no midpoint direction
        self.assertLessEqual(diff[:, off_axis].max(), 0.5 * np.pi / N + 1e-9)

    def test_axial_sum_is_the_sum_over_ring_pairs(self):
        rng = np.random.default_rng(1)
        a, b = rng.random((sg.RINGS, 3)), rng.random((sg.RINGS, 3))
        for mrd in (47, 10, 0):
            want = np.zeros((95, 3))
            for ra in range(sg.RINGS):
                for rb in range(sg.RINGS):
                    if abs(ra - rb) <= mrd:
                        want[ra + rb] += a[ra] * b[rb]
            self.assertLess(np.abs(sg.axial_sum(a, b, mrd) - want).max(), 1e-9, mrd)
        self.assertEqual(sg.ring_pairs_per_slice()[47], 48)
        self.assertEqual(sg.ring_pairs_per_slice()[0], 1)


class Randoms(unittest.TestCase):
    def test_singles_in_coincidence_are_subtracted(self):
        h = header()
        s = np.full(sg.RINGS * N, 1e5)
        r = cor.randoms_from_singles(s, 4000, 10.0, h, in_coincidence=np.full(sg.RINGS * N, 2e4))
        want = cor.randoms_from_singles(np.full(sg.RINGS * N, 8e4), 4000, 10.0, h)
        self.assertLess(np.abs(r - want).max(), 1e-12)

    def test_uniform_singles(self):
        h = header()
        s = np.full(sg.RINGS * N, 1e5)  # counts in 10 s: 10 kHz per crystal
        r = cor.randoms_from_singles(s, 4000, 10.0, h)
        per_lor = 2 * 4000e-12 * 1e4 * 1e4 * 10.0  # 2 tau s_a s_b t
        want = per_lor * sg.ring_pairs_per_slice()[:, None, None]
        self.assertLess(np.abs(r / want - 1).max(), 1e-9)

    def test_follows_each_crystals_rate(self):
        h = header()
        s = np.full((sg.RINGS, N), 1e5)
        s[5, 10] *= 3.0
        r = cor.randoms_from_singles(s.ravel(), 4000, 10.0, h, max_ring_difference=0)
        ti, tj = sg.crystal_pairs(h)
        hot = (ti == 10) | (tj == 10)
        self.assertAlmostEqual(r[10][hot].mean() / r[10][~hot].mean(), 3.0, places=9)
        self.assertAlmostEqual(r[12][hot].mean() / r[12][~hot].mean(), 1.0, places=9)
        self.assertEqual(r[11].max(), 0.0, "an odd slice holds no ring pair at mrd 0")


def efficiency_scan(rng, eff, m):
    """m coincidences of a centered source: crystal a anywhere, b in a fan of +-60 across the ring
    and in any ring, kept with the probability eff_a * eff_b."""
    a = rng.integers(0, sg.RINGS * N, m)
    ta = a % N
    tb = (ta + N // 2 + rng.integers(-60, 61, m)) % N
    b = rng.integers(0, sg.RINGS, m) * N + tb
    keep = rng.random(m) < eff.ravel()[a] * eff.ravel()[b]
    return a[keep], b[keep]


class Normalization(unittest.TestCase):
    def test_fan_sums_find_each_crystals_efficiency(self):
        rng = np.random.default_rng(2)
        eff = np.clip(rng.normal(0.9, 0.05, (sg.RINGS, N)), 0.05, 1.0)
        a, b = efficiency_scan(rng, eff, 40_000_000)
        found = cor.crystal_efficiencies(a, b, np.zeros(a.size, dtype=bool))
        truth = eff / eff.mean(axis=1, keepdims=True)
        err = found / truth - 1
        expected = 1 / np.sqrt(2 * a.size / eff.size)  # Poisson, per fan
        self.assertLess(err.std(), 1.15 * expected)
        self.assertLess(abs(err.mean()), 1e-3)

    def test_delayeds_are_subtracted(self):
        a = np.array([0, 0, 1])
        b = np.array([400, 401, 402])
        f = cor.fan_sums(a, b, np.where(np.array([False, True, False]), -1.0, 1.0))
        self.assertEqual(f.ravel()[0], 0.0)
        self.assertEqual(f.ravel()[1], 1.0)

    def test_products_are_the_mean_over_ring_pairs(self):
        h = header()
        eff = np.ones((sg.RINGS, N))
        eff[0, 3] = 0.5
        p = cor.efficiency_products(eff, h)
        ti, tj = sg.crystal_pairs(h)
        with3 = (ti == 3) | (tj == 3)
        self.assertAlmostEqual(p[0][with3].max(), 0.5)  # slice 0 is ring pair (0, 0) only
        self.assertAlmostEqual(p[1][with3].max(), 0.75)  # (0, 1) and (1, 0)
        self.assertAlmostEqual(p[1][~with3 & (ti >= 0)].min(), 1.0)

    def test_geometric_factors_divide_out_the_source(self):
        h = header()
        rng = np.random.default_rng(3)
        g_true = (1.0 + 0.2 * np.cos(h.s_mm / 40.0))[None, :] * np.linspace(0.5, 1.0, 95)[:, None]
        eff = np.clip(rng.normal(1.0, 0.05, (sg.RINGS, N)), 0.5, 1.5)
        prod = cor.efficiency_products(eff, h)
        chord = cor.cylinder_chords(h, 118.0)
        scan = prod * g_true[:, None, :] * chord[None, None, :]
        g = cor.geometric_factors(scan, prod, h, 118.0)
        inside = chord >= 20.0
        ratio = g[:, inside] / g_true[:, inside]
        self.assertLess(ratio.std() / ratio.mean(), 1e-9)


class Attenuation(unittest.TestCase):
    def test_a_line_in_the_plane(self):
        h = header()
        a = cor.attenuation_factors(h, 90.0, max_ring_difference=0)
        want = np.exp(-cor.MU_WATER_PER_MM * cor.cylinder_chords(h, 90.0))
        self.assertLess(np.abs(a[0, 0] - want).max(), 1e-12)
        self.assertLess(np.abs(a[1, 0] - 1.0).max(), 1e-12,
                        "an odd slice holds no ring pair at mrd 0")
        self.assertAlmostEqual(a[0, 0, h.radial_bins // 2], np.exp(-0.0096 * 180.0), places=12)

    def test_oblique_lines_are_longer(self):
        h = header()
        a = cor.attenuation_factors(h, 90.0)
        flat = cor.attenuation_factors(h, 90.0, max_ring_difference=0)
        mid = h.radial_bins // 2
        self.assertLess(a[47, 0, mid], flat[0, 0, mid])
        self.assertEqual(a[0, 0, mid], flat[0, 0, mid])  # slice 0: ring pair (0, 0) only
        outside = np.abs(h.s_mm) > 90.0
        self.assertTrue((a[:, :, outside] == 1.0).all())


class Scatter(unittest.TestCase):
    def test_tail_fit_recovers_a_gaussian_scatter(self):
        h = header()
        s = h.s_mm
        rng = np.random.default_rng(4)
        scale = rng.uniform(50, 100, (95, 1))  # one scale per slice, shared by its views
        scatter = np.broadcast_to(scale[..., None] * np.exp(-0.5 * (s / 70.0) ** 2),
                                  (95, h.views, h.radial_bins))
        trues = 400.0 * cor.cylinder_chords(h, 80.0) / 160.0
        est, sigma = cor.tail_fit_scatter(scatter + trues, h, 80.0, margin_mm=5.0, width_mm=40.0)
        self.assertAlmostEqual(sigma, 70.0, places=6)
        self.assertLess(np.abs(est / scatter - 1).max(), 1e-9)

    def test_tail_fit_scales_a_model_shape(self):
        h = header()
        s = h.s_mm
        shape = np.clip(1.0 - (s / 100.0) ** 2, 0.0, None) ** 2  # not a Gaussian
        scatter = 3.0 * np.broadcast_to(shape, (95, h.views, h.radial_bins))
        trues = 400.0 * cor.cylinder_chords(h, 80.0) / 160.0
        est, sigma = cor.tail_fit_scatter(scatter + trues, h, 80.0, shape=shape)
        self.assertIsNone(sigma)
        self.assertLess(np.abs(est - scatter).max(), 1e-9)

    def test_tail_fit_of_poisson_counts_with_low_sensitivity_bins(self):
        # Bins whose sensitivity n is 0.01 to 1 (the axial ends, a dead crystal's neighbors) and
        # a few counts each in the tails, one scale per slice: the likelihood scale's error is the
        # Poisson error of the slice's tail counts. A least-squares fit to counts / n weights the
        # bins of low n as much as the others and is 1.5 times as noisy here.
        h = header()
        s = h.s_mm
        rng = np.random.default_rng(5)
        shape = np.broadcast_to(np.exp(-0.5 * (s / 60.0) ** 2), (95, h.views, h.radial_bins))
        n = rng.uniform(0.01, 1.0, shape.shape)
        counts = rng.poisson(0.5 * shape * n)
        est, _ = cor.tail_fit_scatter(counts / n, h, 80.0, shape=shape, sensitivity=n)
        scale = est[:, 0, 113] / 0.5
        tails = (np.abs(s) >= 82.0) & (np.abs(s) <= 102.0)
        poisson = 1.0 / np.sqrt((0.5 * shape * n)[..., tails].sum(axis=(1, 2)))
        self.assertLess(np.sqrt(((scale - 1) ** 2).mean()), 1.2 * np.sqrt((poisson ** 2).mean()))
        self.assertAlmostEqual(scale.mean(), 1.0, delta=0.01)


class DeadTimeAndDecay(unittest.TestCase):
    def test_live_fractions(self):
        n = np.array([1e5, 5e5, 1e6])  # true rates per s
        tau = 200.0                     # ns
        m_np = n / (1 + n * tau * 1e-9)
        live = cor.live_fractions(m_np * 10, 10.0, tau)
        self.assertLess(np.abs(live - m_np / n).max(), 1e-12)
        m_p = n * np.exp(-n * tau * 1e-9)
        live = cor.live_fractions(m_p * 10, 10.0, tau, "paralyzable")
        self.assertLess(np.abs(live - m_p / n).max(), 1e-9)
        with self.assertRaises(ValueError):
            cor.live_fractions(n, 1.0, tau, "linear")
        self.assertAlmostEqual(cor.pair_live_fraction([0.9, 0.9, 0.9]), 0.81)
        self.assertAlmostEqual(cor.pair_live_fraction([1.0, 0.5]), 0.5)

    def test_decay(self):
        half = 6586.2  # s: F-18, 109.77 minutes
        self.assertAlmostEqual(cor.decay_factor(half, 0.0, half), 2.0)
        self.assertAlmostEqual(cor.decay_factor(0.0, 1e-6, half), 1.0, places=9)
        # The mean activity over a frame, integrated numerically.
        t = np.linspace(600.0, 1800.0, 200_001)
        mean = np.exp(-np.log(2) * t / half).mean()
        self.assertAlmostEqual(cor.decay_factor(600.0, 1200.0, half) * mean, 1.0, places=6)


class Compatibility(unittest.TestCase):
    def records(self):
        c = {"format": 1, "energy_window_kev": [435.0, 585.0], "coincidence_window_ps": 4000,
             "window_mode": "fixed"}
        cal = {"id": "CAL-0002", "version": 2, "crc32": "6c696a72"}
        return ({"run": {"corrections": dict(c), "calibration": dict(cal)}},
                {"run": {"corrections": dict(c), "calibration": dict(cal)}})

    def test_refuses_a_normalization_from_other_settings(self):
        # REQ: SRS-COR-003
        norm, run = self.records()
        self.assertEqual(cor.incompatibilities(norm, run), [])
        for key, value in (("energy_window_kev", [425.0, 650.0]), ("coincidence_window_ps", 3000),
                           ("window_mode", "per_single")):
            norm, run = self.records()
            norm["run"]["corrections"][key] = value
            problems = cor.incompatibilities(norm, run)
            self.assertEqual(len(problems), 1, key)
            self.assertIn(key, problems[0])
        norm, run = self.records()
        run["run"]["calibration"]["crc32"] = "00000000"
        self.assertIn("calibration", cor.incompatibilities(norm, run)[0])
        norm, run = self.records()
        del norm["run"]["calibration"]  # a simulated scan: the identity, unlike the run's table
        self.assertIn("calibration", cor.incompatibilities(norm, run)[0])
        norm, run = self.records()
        del run["run"]["corrections"]
        self.assertIn("no corrections", cor.incompatibilities(norm, run)[0])


DEFAULT_METADATA = b'{"records":{"delayed_window_ps":100000}}'


def write_listmode(path, records, metadata=DEFAULT_METADATA, damage=None):
    """A minimal MDQ-L1 file, as docs/formats/mdq-l1.md specifies it: one block."""
    meta_pad = metadata + b"\0" * (-len(metadata) % 8)
    head = bytearray(b"MDQL\r\n\x1a\n" + (1).to_bytes(2, "little") + (0).to_bytes(2, "little"))
    head += (40 + len(meta_pad)).to_bytes(4, "little") + len(metadata).to_bytes(4, "little")
    head += bytes(4) + (16).to_bytes(4, "little") + bytes(4) + meta_pad
    head += zlib.crc32(head).to_bytes(4, "little") + bytes(4)
    body = records.tobytes()
    block = bytearray(b"MDQB" + (0).to_bytes(4, "little") + len(records).to_bytes(4, "little"))
    block += (1).to_bytes(4, "little") + (1000).to_bytes(8, "little", signed=True)
    block += zlib.crc32(body).to_bytes(4, "little")
    block += zlib.crc32(block).to_bytes(4, "little")
    raw = bytearray(head + block + body)
    if damage is not None:
        raw[damage] ^= 0x01
    pathlib.Path(path).write_bytes(raw)


class Projection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = header()
        cls.s, cls.phi = project.bin_lines(cls.h)
        cls.A = project.Projector(cls.s, cls.phi, n=96, pixel_mm=2.5)

    def test_each_view_interleaves_two_angles(self):
        # The pair (i, j) has its normal at (i + j + 1) pi / N; r odd and r even alternate.
        ti, tj = sg.crystal_pairs(self.h)
        v, c = 10, np.flatnonzero(ti[10] >= 0)[:6]
        k = ti[v, c] + tj[v, c] + 1
        k = np.where(k >= sg.CRYSTALS_PER_RING, k - sg.CRYSTALS_PER_RING, k)
        self.assertTrue(np.allclose(self.phi[v, c], k * np.pi / sg.CRYSTALS_PER_RING))
        self.assertAlmostEqual(self.phi[v].mean(), self.h.phi[v], delta=0.01 * np.pi / 384)

    def test_the_backprojector_is_the_adjoint(self):
        rng = np.random.default_rng(6)
        x = rng.random((96, 96))
        y = rng.random(self.s.shape)
        lhs = (self.A.forward(x) * y).sum()
        rhs = (x * self.A.back(y)).sum()
        self.assertAlmostEqual(lhs / rhs, 1.0, delta=1e-6)

    def test_a_disc_projects_to_its_chords(self):
        xs, ys = self.A.pixel_centers()
        disc = ((xs ** 2 + ys ** 2) <= 80.0 ** 2).astype(float)
        got = self.A.forward(disc)
        want = 2.0 * np.sqrt(np.clip(80.0 ** 2 - self.s ** 2, 0.0, None))
        inner = np.abs(self.s) < 70.0
        # A disc of square pixels has a ragged edge: about half a pixel of chord on each side.
        self.assertLess(np.abs(got - want)[inner].mean(), 1.0)
        self.assertLess(np.abs(got - want)[inner].max(), 4.0)

    def test_an_off_center_object_lies_on_its_sinusoid(self):
        xs, ys = self.A.pixel_centers()
        blob = np.exp(-0.5 * ((xs - 40.0) ** 2 + (ys + 25.0) ** 2) / 3.0 ** 2)
        got = self.A.forward(blob)
        peak = self.s[np.arange(self.s.shape[0]), got.argmax(axis=1)]
        want = 40.0 * np.cos(self.phi[:, 0]) - 25.0 * np.sin(self.phi[:, 0])
        self.assertLess(np.abs(peak - want).max(), 1.6)  # half a radial bin at s = 47 mm


class Reconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = header()
        s, phi = project.bin_lines(cls.h)
        cls.A = project.Projector(s, phi, n=64, pixel_mm=3.75)
        xs, ys = cls.A.pixel_centers()
        x = ((xs ** 2 + ys ** 2) <= 80.0 ** 2).astype(float)
        x[(xs - 35.0) ** 2 + ys ** 2 <= 15.0 ** 2] = 4.0
        cls.truth = x
        rng = np.random.default_rng(7)
        cls.mult = rng.uniform(0.3, 1.0, s.shape)  # normalization and attenuation
        cls.add = np.full(s.shape, 0.5)            # randoms and scatter
        cls.mean = mlem.expected(x, cls.A, cls.mult, cls.add)
        cls.y = rng.poisson(cls.mean).astype(float)

    def test_mlem_never_lowers_the_likelihood(self):
        ll = []
        mlem.osem(self.y, self.A, self.mult, self.add, 12,
                  callback=lambda it, x: ll.append(
                      mlem.log_likelihood(self.y, mlem.expected(x, self.A, self.mult, self.add))))
        self.assertTrue(all(b >= a - 1e-6 * abs(a) for a, b in zip(ll, ll[1:])), ll)

    def test_one_subset_is_mlem_and_subsets_go_faster(self):
        a = mlem.osem(self.y, self.A, self.mult, self.add, 3, n_subsets=1)
        b = mlem.osem(self.y, self.A, self.mult, self.add, 3)
        self.assertTrue(np.array_equal(a, b))
        ll = lambda x: mlem.log_likelihood(self.y, mlem.expected(x, self.A, self.mult, self.add))
        fast = mlem.osem(self.y, self.A, self.mult, self.add, 3, n_subsets=8)
        slow = mlem.osem(self.y, self.A, self.mult, self.add, 24)
        self.assertGreater(ll(fast), ll(a))
        self.assertAlmostEqual((ll(fast) - ll(a)) / (ll(slow) - ll(a)), 1.0, delta=0.05)

    def test_noiseless_data_give_the_object(self):
        x = mlem.osem(self.mean, self.A, self.mult, self.add, 40, n_subsets=8)
        xs, ys = self.A.pixel_centers()
        inside = (xs ** 2 + ys ** 2 <= 70.0 ** 2) & ((xs - 35.0) ** 2 + ys ** 2 > 20.0 ** 2)
        hot = (xs - 35.0) ** 2 + ys ** 2 <= 10.0 ** 2
        self.assertAlmostEqual(x[inside].mean(), 1.0, delta=0.02)
        self.assertAlmostEqual(x[hot].mean(), 4.0, delta=0.12)
        self.assertGreaterEqual(x.min(), 0.0)

    def test_subsets_must_cover_the_views(self):
        self.assertEqual(sorted(sum(mlem.subsets(192, 8), [])), list(range(192)))
        with self.assertRaises(ValueError):
            mlem.subsets(192, 0)


class ListMode(unittest.TestCase):
    def records(self):
        r = np.zeros(3, dtype=listmode.RECORD)
        r["time_offset"] = [0, 5, 9]
        r["crystal_a"] = [10, 0x7FFF, 20 | 0x8000]
        r["crystal_b"] = [200, 1, 300]
        r["dt_ps"] = [100, 0, 100_050]
        r["energy_a"] = [511 * 32, 0, 500 * 32]
        return r

    def test_reads_events_and_skips_tags(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "a.mdql"
            write_listmode(p, self.records())
            meta, c = listmode.read_file(p)
            self.assertEqual(meta["records"]["delayed_window_ps"], 100000)
            self.assertEqual(c["crystal_a"].tolist(), [10, 20])
            self.assertEqual(c["crystal_b"].tolist(), [200, 300])
            self.assertEqual(c["delayed"].tolist(), [False, True])
            self.assertEqual(c["time_ps"].tolist(), [1000, 1009])
            self.assertEqual(c["energy_a_kev"].tolist(), [511.0, 500.0])

    def test_refuses_a_damaged_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "a.mdql"
            for at in (0, 20, -1, -16 * 3 - 5):  # magic, file header, a record, the block header
                write_listmode(p, self.records(), damage=at)
                with self.assertRaises(listmode.FormatError, msg=str(at)):
                    listmode.read_file(p)


class EndToEnd(unittest.TestCase):
    """One short simulated run: the Python reader and bins against minidaq_listmode sino."""

    def test_bins_agree_with_the_histogrammer(self):
        # REQ: SRS-COR-002
        if BIN_DIR is None:
            self.skipTest("no program directory given")
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "lm").mkdir()
            subprocess.run([str(BIN_DIR / "minidaq_sim"), "--activity", "5e6", "--seconds", "0.05",
                            "--efficiency-spread", "0.05", "--listmode", str(d / "lm"),
                            "--truth-sino", str(d / "lm" / "truth")],
                           check=True, capture_output=True)
            files = sorted((d / "lm").glob("*.mdql"))
            subprocess.run([str(BIN_DIR / "minidaq_listmode"), "sino", "--out", str(d / "s"),
                            *map(str, files)], check=True, capture_output=True)
            h = sg.read_header(d / "s.hdr")
            record, c = listmode.read_run(next((d / "lm").glob("*.run.json")))
            mine = {k: np.zeros(h.shape) for k in ("prompts", "delayeds")}
            # Each coincidence's bin, from the same pairing.
            ti, tj = sg.crystal_pairs(h)
            where = np.full((N, N, 2), -1, dtype=np.int64)
            v, col = np.nonzero(ti >= 0)
            where[ti[v, col], tj[v, col]] = np.stack([v, col], axis=1)
            where[tj[v, col], ti[v, col]] = np.stack([v, col], axis=1)
            ra, rb = sg.ring_of(c["crystal_a"]), sg.ring_of(c["crystal_b"])
            vc = where[sg.transaxial_of(c["crystal_a"]), sg.transaxial_of(c["crystal_b"])]
            ok = (vc[:, 0] >= 0) & (np.abs(ra - rb) <= h.max_ring_difference)
            for k, sel in (("prompts", ~c["delayed"]), ("delayeds", c["delayed"])):
                m = ok & sel
                np.add.at(mine[k], (ra[m] + rb[m], vc[m, 0], vc[m, 1]), 1.0)
                self.assertTrue(np.array_equal(mine[k], sg.read(h, k)), k)
            # The truth sinograms add up to the prompts.
            t = sg.read_header(d / "lm" / "truth.hdr")
            parts = sum(sg.read(t, k) for k in ("trues", "scatters", "randoms"))
            self.assertTrue(np.array_equal(parts, sg.read(t, "prompts")))
            self.assertTrue(np.array_equal(sg.read(t, "prompts"), mine["prompts"]))
            # The run record's corrections: every crystal's singles.
            k = record["run"]["corrections"]
            self.assertEqual(len(k["singles_per_crystal"]), sg.RINGS * N)
            self.assertEqual(sum(k["singles_per_crystal"]), k["singles_in_window"])
            self.assertEqual(k["prompts"], int((~c["delayed"]).sum()))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        BIN_DIR = pathlib.Path(sys.argv.pop(1))
    unittest.main()
