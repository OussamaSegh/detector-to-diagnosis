#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 39 measurements: what time of flight gives and what it asks of the time base.

The scanner is MiniDAQ's simulated one with perfect crystals, and the objects are in air, so that
neither attenuation nor scatter enters the comparison: the data are prompts, the model's additive
term the randoms from the singles (Chapter 27), and its multiplicative term the normalization of
two scans of a cylinder of radius 118 mm. The 2D sinograms are every slice added
(tools/recon/sinogram.py bin_2d), the lines at 156 mm (measurements/ch28), the images 128 x 128
pixels of 2 mm, OSEM with 8 subsets; TOF bins of 100 ps (15 mm along a line), 21 of them.

1. Timing resolution: a point source at the center, the simulator's coincidence time resolution
   set to 200, 300 and 500 ps FWHM. The FWHM of the measured tau of the prompts.
2. Noise: a uniform cylinder of radius 100 mm and length 100 mm, 2e7 Bq for 3 s, with a hot rod
   of radius 10 mm at (50, 0) mm and four times the concentration, at 300 and at 500 ps. Per
   iteration, without TOF and with it: the rod's contrast recovery and the background's noise
   after a Gaussian post-filter of 8 mm FWHM, the background variability of 15 regions of radius
   8 mm (unfiltered), the unfiltered pixel noise, and the background mean's ratio to the
   non-TOF one.
3. A clock off: a point source at (40, -25) mm, 2e6 Bq for 1 s, at 300 ps. Every single of block
   29, or of a quarter of the scanner (the blocks 4 to 9 of each block ring, as one branch of a
   clock fan-out), is stamped late by an offset (applied to the list mode, as a clock off by that
   much would stamp it), and the image is reconstructed with and without TOF: the share of the
   image within 8 mm of the point.
4. Cost: one projection and one backprojection of the whole sinogram by the C++ projector, with
   and without TOF.

    python3 measurements/ch39/tof.py build/release [WORK_DIR] > measurements/ch39/tof.txt

The argument is a build directory with minidaq/apps and recon (the module recon_cpp).
"""
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np

BUILD = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release")
APPS = BUILD / "minidaq" / "apps"
os.environ.setdefault("MINIDAQ_RECON_CPP", str(BUILD / "recon"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import chain, listmode, mlem, project
from tools.recon import sinogram as sg

RADIUS_MM = 156.0
N, PIXEL_MM, SUBSETS = 128, 2.0, 8
TOF_BINS, TOF_BIN_PS = 21, 100.0
BLOCK = 29
QUARTER = [b for b in range(72) if b % 24 in range(4, 10)]
POINT = (40.0, -25.0)
ROD = (10.0, 50.0, 0.0)  # radius, x, y in mm
ITERATIONS = 12


def simulate(work, name, args, seed):
    d = work / name
    if list(d.glob("*.run.json")) and (d / "truth.hdr").exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "sim.txt", "w") as out:
        subprocess.run([str(APPS / "minidaq_sim"), *args, "--seed", str(seed), "--listmode", str(d),
                        "--truth-sino", str(d / "truth")], check=True, stdout=out)


def coincidences(work, name):
    record, c = listmode.read_run(next((work / name).glob("*.run.json")))
    return record, c


def section(title):
    print(f"\n## {title}\n")


def fwhm(profile, step):
    p = np.asarray(profile, dtype=np.float64)
    k = int(p.argmax())
    half = p[k] / 2.0
    lo, hi = k, k
    while lo > 0 and p[lo] > half:
        lo -= 1
    while hi < p.size - 1 and p[hi] > half:
        hi += 1
    left = lo + (half - p[lo]) / (p[lo + 1] - p[lo])
    right = hi - 1 + (p[hi - 1] - half) / (p[hi - 1] - p[hi])
    return (right - left) * step


# [snippet:block-clock]
def clock_off(c, blocks, offset_ps):
    """The coincidences as blocks whose clock is offset_ps late would have stamped them: each of
    their singles is offset_ps later, so dt grows when it is the later single and shrinks when it
    is the earlier; a prompt pair whose order flips swaps its crystals, since crystal_a is the
    earlier. (A delayed pair's second single is a delay late, and stays the later one.)"""
    a_in = np.isin(sg.block_of(c["crystal_a"]), blocks)
    b_in = np.isin(sg.block_of(c["crystal_b"]), blocks)
    dt = c["dt_ps"].astype(np.int64) + offset_ps * (b_in.astype(np.int64) - a_in.astype(np.int64))
    flip = ~c["delayed"] & (dt < 0)
    out = dict(c)
    out["crystal_a"] = np.where(flip, c["crystal_b"], c["crystal_a"])
    out["crystal_b"] = np.where(flip, c["crystal_a"], c["crystal_b"])
    out["dt_ps"] = np.abs(dt)
    return out
# [/snippet:block-clock]


def gaussian_filter(img, fwhm_mm, pixel_mm):
    """A separable Gaussian, by FFT (numpy only), with zero padding (as measurements/ch28)."""
    sigma = fwhm_mm / (2.0 * np.sqrt(2.0 * np.log(2.0))) / pixel_mm
    n = img.shape[0]
    size = 2 * n
    g = np.exp(-2.0 * (np.pi * sigma * np.fft.rfftfreq(size)) ** 2)
    out = np.fft.irfft(np.fft.rfft(img, size, axis=1) * g, size, axis=1)[:, :n]
    return np.fft.irfft(np.fft.rfft(out, size, axis=0) * g[:, None], size, axis=0)[:n, :]


def main():
    work_arg = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = None if work_arg else tempfile.TemporaryDirectory()
    work = pathlib.Path(work_arg or tmp.name)
    work.mkdir(parents=True, exist_ok=True)
    print("# Chapter 39: time of flight\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}.")
    t0 = time.monotonic()
    air = ["--phantom", "0"]
    for ctr in (200, 300, 500):
        simulate(work, f"center{ctr}", ["--source", "point", "--center", "0,0,0", *air,
                                        "--activity", "1e6", "--seconds", "1", "--ctr", str(ctr)],
                 3900 + ctr)
    for k in (1, 2):
        simulate(work, f"norm{k}", ["--activity", "1e7", "--seconds", "5", *air,
                                    "--source-radius", "118", "--source-length", "120"], k)
    for ctr in (300, 500):
        simulate(work, f"cylinder{ctr}", ["--activity", "2e7", "--seconds", "3", *air,
                                          "--source-radius", "100", "--source-length", "100",
                                          "--ctr", str(ctr)], 3910 + ctr)
    for ctr in (300, 500):
        r, x, y = ROD
        extra = 3.0 * 2e7 * (r / 100.0) ** 2
        simulate(work, f"rod{ctr}", ["--activity", f"{extra:.6g}", "--seconds", "3", *air,
                                     "--source-radius", str(r), "--source-length", "100",
                                     "--center", f"{x},{y},0", "--ctr", str(ctr)], 3950 + ctr)
    simulate(work, "point", ["--source", "point", "--center", f"{POINT[0]},{POINT[1]},0", *air,
                             "--activity", "2e6", "--seconds", "1", "--ctr", "300"], 3920)
    print(f"Simulated in {time.monotonic() - t0:.0f} s (0 if the runs were reused).")

    # 1. Timing resolution.
    section("1. Timing resolution: a point source at the center")
    print("| Set, ps FWHM | Measured, ps FWHM | Prompts |")
    print("|---:|---:|---:|")
    for ctr in (200, 300, 500):
        _, c = coincidences(work, f"center{ctr}")
        prompt = ~c["delayed"]
        # At the center both photons travel 156 mm or so: tau is the timing error alone. Which
        # single is earlier is chance, so the signed tau of a fixed end of each line is used.
        tau = np.where(sg.transaxial_of(c["crystal_a"]) < sg.transaxial_of(c["crystal_b"]),
                       -c["dt_ps"], c["dt_ps"])[prompt]
        hist, _ = np.histogram(tau, bins=np.arange(-1500, 1501, 20))
        print(f"| {ctr} | {fwhm(hist, 20.0):.0f} | {prompt.sum():,} |")
    print("\nThe width is that of tau over every line through the center, within a few percent of the "
          "set resolution: a little more at 200 and 300 ps, since the photons interact at different "
          "depths in their crystals, an effect lost in the 20 ps bins at 500 ps.")

    # 2. Noise.
    section("2. Noise: a uniform cylinder of radius 100 mm in air, with a hot rod")
    norm_dirs = [work / f"norm{k}" for k in (1, 2)]
    n_bins, _, _ = chain.normalization(norm_dirs, 118.0)
    h = sg.read_header(work / "norm1" / "truth.hdr")
    mult = n_bins.sum(axis=0)
    s, phi = project.bin_lines(h, RADIUS_MM)
    plain = project.CppProjector(s, phi, n=N, pixel_mm=PIXEL_MM)
    xs, ys = plain.pixel_centers()
    r_rod, x_rod, y_rod = ROD
    d_rod = np.hypot(xs - x_rod, ys - y_rod)
    rod = d_rod <= r_rod / 2.0
    bg = (np.hypot(xs, ys) <= 70.0) & (d_rod > r_rod + 15.0)
    centers = [(r * np.cos(t), r * np.sin(t)) for r in (30.0, 55.0) for t in np.arange(8) * np.pi / 4]
    rois = [np.hypot(xs - cx, ys - cy) <= 8.0 for cx, cy in [(0.0, 0.0), *centers]
            if np.hypot(cx - x_rod, cy - y_rod) > r_rod + 18.0]

    def metrics(x):
        f = gaussian_filter(x, 8.0, PIXEL_MM)
        means = np.array([x[r].mean() for r in rois])
        return ((f[rod].mean() / f[bg].mean() - 1.0) / 3.0, f[bg].std() / f[bg].mean(),
                means.std() / means.mean(), x[bg].std() / x[bg].mean(), x[bg].mean())

    for ctr in (300, 500):
        runs = [f"cylinder{ctr}", f"rod{ctr}"]
        parts = [coincidences(work, r) for r in runs]
        c = {k: np.concatenate([p[1][k] for p in parts]) for k in parts[0][1]}
        window = parts[0][0]["run"]["corrections"]["coincidence_window_ps"]
        randoms = sum(chain.randoms(work / r, h) for r in runs).sum(axis=0)
        y, _ = sg.bin_2d(c, h)
        yt, _ = chain.tof_sinograms(work / f"rod{ctr}", h, TOF_BINS, TOF_BIN_PS)
        tof = project.CppTofProjector(s, phi, n=N, pixel_mm=PIXEL_MM, tof_bins=TOF_BINS,
                                      tof_bin_ps=TOF_BIN_PS, ctr_fwhm_ps=float(ctr))
        series = {}
        for label, A, data, m, a in (
                ("without", plain, y, mult, randoms),
                ("with", tof, yt, mult[..., None], (randoms * TOF_BIN_PS / window)[..., None])):
            rows = []
            mlem.osem(data, A, m, a, ITERATIONS, n_subsets=SUBSETS,
                      callback=lambda it, x, rows=rows: rows.append(metrics(x)))
            series[label] = rows
        print(f"At {ctr} ps: {int(y.sum()):,} prompts in the sinogram, {int(yt.sum()):,} of them "
              f"in the TOF bins. Without TOF / with TOF:\n")
        print("| Iteration | Rod's contrast recovery | Noise, 8 mm filter | Background variability, "
              "15 regions | Pixel noise, unfiltered | TOF mean / non-TOF mean |")
        print("|---:|---:|---:|---:|---:|---:|")
        for it in range(ITERATIONS):
            p, t = series["without"][it], series["with"][it]
            print(f"| {it + 1} | {p[0]:.2f} / {t[0]:.2f} | {100 * p[1]:.1f}% / {100 * t[1]:.1f}% | "
                  f"{100 * p[2]:.2f}% / {100 * t[2]:.2f}% | {100 * p[3]:.1f}% / {100 * t[3]:.1f}% | "
                  f"{t[4] / p[4]:.3f} |")
        p, t = series["without"][-1], series["with"][-1]
        dx = ctr * project.C_MM_PER_PS / 2.0
        print(f"\nAfter {ITERATIONS} iterations the filtered noise falls by a factor of "
              f"{p[1] / t[1]:.2f} and the background variability by {p[2] / t[2]:.2f}; "
              f"sqrt(D / dx) for D = 200 mm and dx = c * {ctr} ps / 2 = {dx:.0f} mm is "
              f"{np.sqrt(200.0 / dx):.2f}.\n")

    # 3. A clock off.
    section(f"3. A clock off: a point source at ({POINT[0]:.0f}, {POINT[1]:.0f}) mm")
    record, c = coincidences(work, "point")
    window = record["run"]["corrections"]["coincidence_window_ps"]
    randoms = chain.randoms(work / "point", h).sum(axis=0)
    tof = project.CppTofProjector(s, phi, n=N, pixel_mm=PIXEL_MM, tof_bins=TOF_BINS,
                                  tof_bin_ps=TOF_BIN_PS, ctr_fwhm_ps=300.0)
    near = np.hypot(xs - POINT[0], ys - POINT[1]) <= 8.0
    prompts = ~c["delayed"]
    for name, blocks in ((f"block {BLOCK}", [BLOCK]), ("a quarter of the scanner", QUARTER)):
        hit = np.isin(sg.block_of(c["crystal_a"]), blocks) | np.isin(sg.block_of(c["crystal_b"]), blocks)
        on = (hit & prompts).sum()
        print(f"\nThe clock of {name} ({len(blocks)} block{"s" if len(blocks) > 1 else ""}) off: {on:,} of {prompts.sum():,} prompts "
              f"({100 * on / prompts.sum():.0f}%) have a single there.\n")
        print("| Offset, ps | Share within 8 mm, without TOF | Share within 8 mm, with TOF |")
        print("|---:|---:|---:|")
        for offset in (0, 100, 250, 400, 800):
            cc = clock_off(c, blocks, offset)
            y, _ = sg.bin_2d(cc, h)
            yt, _ = sg.bin_2d(cc, h, TOF_BINS, TOF_BIN_PS)
            x0 = mlem.osem(y, plain, mult, randoms, 5, n_subsets=SUBSETS)
            x1 = mlem.osem(yt, tof, mult[..., None], (randoms * TOF_BIN_PS / window)[..., None], 5,
                           n_subsets=SUBSETS)
            print(f"| {offset} | {100 * x0[near].sum() / x0.sum():.1f}% | "
                  f"{100 * x1[near].sum() / x1.sum():.1f}% |")
    try:
        chain.check_time_base_for_tof({"run": {"timing": {"alarm_intervals": 3, "blocks": [
            {"alarm_intervals": 3 if i == BLOCK else 0} for i in range(72)]}}})
    except chain.TimeBaseError as e:
        print(f"\nThe guard on such a run (its monitor at alarm, Chapter 38): {e}.")

    # 4. Cost.
    section("4. Cost of one projection and one backprojection (C++ projector)")
    print("| Projector | Threads | Forward, s | Back, s |")
    print("|---|---:|---:|---:|")
    image = np.random.default_rng(39).random((N, N))
    for label, make in (("without TOF", lambda t: project.CppProjector(s, phi, N, PIXEL_MM, t)),
                        (f"TOF, {TOF_BINS} bins", lambda t: project.CppTofProjector(
                            s, phi, N, PIXEL_MM, TOF_BINS, TOF_BIN_PS, 300.0, t))):
        for threads in (1, 0):
            A = make(threads)
            f, b = [], []
            for _ in range(3):
                t0 = time.perf_counter()
                sino = A.forward(image)
                f.append(time.perf_counter() - t0)
                t0 = time.perf_counter()
                A.back(sino)
                b.append(time.perf_counter() - t0)
            shown = threads or os.cpu_count()
            print(f"| {label} | {shown} | {np.median(f):.3f} | {np.median(b):.3f} |")


if __name__ == "__main__":
    main()
