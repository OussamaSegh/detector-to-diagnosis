#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 28 measurements: 2D OSEM on MiniDAQ's simulated data, with Chapter 27's corrections in
the model.

The scanner and the normalization are those of measurements/ch27 (crystal seed 7, efficiencies
spread by 5%; six normalization scans), and so is the background: the cylinder of activity of
radius 80 mm in water of radius 90 mm, 20 MBq for 5 s. Given the same WORK_DIR, the runs of
Chapter 27 are reused.

1. Geometry: a point source at (40, -25, 0) mm in air. Where does it come out, with the lines at
   the crystals' front faces (R = 150 mm) and deeper?
2. A phantom: three hot rods (radius 12, 8 and 5 mm, 100 mm long) at four times the background's
   concentration, each simulated as a run of its own and added to the background run. The data
   are the slices 20 to 74 summed (a 2D sinogram of an object that is uniform along the axis).
   OSEM with 8 subsets: the likelihood, the background's noise and each rod's contrast recovery,
   iteration by iteration.
3. MLEM against OSEM: the same likelihood after the same number of updates?
4. What the corrections in the model do: the background's profile without them.
5. A post-filter: noise against contrast.

    python3 measurements/ch28/reconstruct.py build/release/minidaq/apps [WORK_DIR] \
        > measurements/ch28/reconstruct.txt
"""
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np

APPS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import chain, corrections as cor, mlem, project, sinogram as sg  # noqa: E402

SCANNER = ["--efficiency-spread", "0.05", "--crystal-seed", "7"]
NORM_RUNS = 6
NORM = ["--activity", "1e7", "--seconds", "5", "--phantom", "0", "--source-radius", "118",
        "--source-length", "120"]
PHANTOM = ["--activity", "2e7", "--seconds", "5"]
POINT = (40.0, -25.0)
SOURCE_RADIUS, WATER_RADIUS, BACKGROUND_BQ = 80.0, 90.0, 2e7
CONTRAST = 4.0  # the rods' concentration over the background's
RODS = [(12.0, 40.0, 0.0), (8.0, -20.0, 35.0), (5.0, -20.0, -35.0)]  # radius, x, y in mm
SLICES = slice(20, 75)
N, PIXEL_MM = 128, 2.0
SUBSETS = 8


def simulate(work, name, args, seed, scanner=SCANNER):
    d = work / name
    if (d / "truth.hdr").exists() and list(d.glob("*.run.json")):
        return 0.0
    d.mkdir(parents=True, exist_ok=True)
    truth = ["--crystal-truth", str(work / "crystals.csv")] if scanner else []
    t0 = time.monotonic()
    with open(d / "sim.txt", "w") as out:
        subprocess.run([str(APPS / "minidaq_sim"), *args, *scanner, "--seed", str(seed),
                        "--listmode", str(d), "--truth-sino", str(d / "truth"), *truth],
                       check=True, stdout=out)
    return time.monotonic() - t0


def rod_args(radius, x, y):
    extra = (CONTRAST - 1.0) * BACKGROUND_BQ * (radius / SOURCE_RADIUS) ** 2
    return ["--activity", f"{extra:.6g}", "--seconds", "5", "--centre", f"{x},{y},0",
            "--source-radius", str(radius), "--source-length", "100"]


def section(title):
    print(f"\n## {title}\n")


def pct(x):
    return 100.0 * x


def centroid(img, xs, ys):
    w = np.clip(img - 0.1 * img.max(), 0.0, None)
    return float((w * xs).sum() / w.sum()), float((w * ys).sum() / w.sum())


def fwhm(profile, step_mm):
    """Full width at half maximum of a peaked profile, by linear interpolation."""
    p = np.asarray(profile, dtype=np.float64)
    k = int(p.argmax())
    half = p[k] / 2.0
    lo = k
    while lo > 0 and p[lo] > half:
        lo -= 1
    hi = k
    while hi < p.size - 1 and p[hi] > half:
        hi += 1
    left = lo + (half - p[lo]) / (p[lo + 1] - p[lo])
    right = hi - 1 + (p[hi - 1] - half) / (p[hi - 1] - p[hi])
    return (right - left) * step_mm


def gaussian_filter(img, fwhm_mm, pixel_mm):
    """A separable Gaussian, by FFT (numpy only), with zero padding."""
    sigma = fwhm_mm / (2.0 * np.sqrt(2.0 * np.log(2.0))) / pixel_mm
    n = img.shape[0]
    size = 2 * n
    f = np.fft.rfftfreq(size)
    g = np.exp(-2.0 * (np.pi * sigma * f) ** 2)
    out = np.fft.irfft(np.fft.rfft(img, size, axis=1) * g, size, axis=1)[:, :n]
    out = np.fft.irfft(np.fft.rfft(out, size, axis=0) * g[:, None], size, axis=0)[:n, :]
    return out


def main():
    work_arg = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = None if work_arg else tempfile.TemporaryDirectory()
    work = pathlib.Path(work_arg or tmp.name)
    work.mkdir(parents=True, exist_ok=True)
    print("# Chapter 28: 2D OSEM on simulated MiniDAQ data\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}.")
    t0 = time.monotonic()
    for k in range(1, NORM_RUNS + 1):
        simulate(work, f"norm{k}", NORM, k)
    simulate(work, "phantom", PHANTOM, 1000)
    simulate(work, "scatter_model", PHANTOM, 2000, scanner=[])
    simulate(work, "point", ["--source", "point", "--centre", f"{POINT[0]},{POINT[1]},0",
                             "--phantom", "0", "--activity", "1e6", "--seconds", "2"], 5000)
    for k, rod in enumerate(RODS):
        simulate(work, f"rod{k}", rod_args(*rod), 4001 + k)
    simulate(work, "phantom_b", PHANTOM, 1001)  # a second realization, for section 2
    for k, rod in enumerate(RODS):
        simulate(work, f"rodb{k}", rod_args(*rod), 4101 + k)
    print(f"Simulated in {time.monotonic() - t0:.0f} s (0 if the runs were reused).")

    t0 = time.monotonic()
    n_bins, geo, _ = chain.normalization([work / f"norm{k}" for k in range(1, NORM_RUNS + 1)],
                                         118.0)
    h = sg.read_header(work / "phantom" / "truth.hdr")
    norm_s = time.monotonic() - t0

    # 1. Geometry.
    section("1. Geometry: a point source at (40, -25) mm in air")
    hp = sg.read_header(work / "point" / "truth.hdr")
    yp = sg.read(hp, "prompts").sum(axis=0)
    rp = chain.randoms(work / "point", hp).sum(axis=0)
    mp = n_bins.sum(axis=0)
    print("| Lines at radius | x found | y found | Distance from the axis, found / true | "
          "FWHM x | FWHM y |")
    print("|---|---:|---:|---:|---:|---:|")
    true_r = float(np.hypot(*POINT))
    found = {}
    for radius in (150.0, 156.0):
        s, phi = project.bin_lines(hp, radius)
        A = project.Projector(s, phi, n=128, pixel_mm=1.0)
        img = mlem.osem(yp, A, mp, rp, 10, n_subsets=SUBSETS)
        xs, ys = A.pixel_centers()
        cx, cy = centroid(img, xs, ys)
        found[radius] = (cx, cy)
        j, i = np.unravel_index(img.argmax(), img.shape)
        print(f"| {radius:.0f} mm | {cx:.2f} | {cy:.2f} | {np.hypot(cx, cy) / true_r:.4f} | "
              f"{fwhm(img[j, :], 1.0):.1f} mm | {fwhm(img[:, i], 1.0):.1f} mm |")
    ratio = np.hypot(*found[150.0]) / true_r
    print(f"\nWith the lines at the front faces the point comes out {pct(1 - ratio):.1f}% too "
          "close "
          f"to the axis: the photons interact on average below the front face, so the lines are "
          f"at about {150.0 / ratio:.0f} mm. OSEM, {SUBSETS} subsets, 10 iterations, 1 mm pixels; "
          "the FWHM is of the reconstructed point at that iteration, not the scanner's "
          "resolution (Chapter 30).")
    radius = 150.0 / ratio

    # 2. The phantom.
    s, phi = project.bin_lines(h, radius)
    A = project.Projector(s, phi, n=N, pixel_mm=PIXEL_MM)
    xs, ys = A.pixel_centers()
    runs = ["phantom"] + [f"rod{k}" for k in range(len(RODS))]
    P = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "prompts") for r in runs)
    T = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "trues") for r in runs)
    S_true = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "scatters") for r in runs)
    R_true = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "randoms") for r in runs)
    R = sum(chain.randoms(work / r, h) for r in runs)
    shape = chain.scatter_shape(work / "scatter_model", geo)
    with np.errstate(divide="ignore", invalid="ignore"):
        n_safe = np.where(n_bins > 0, n_bins, 1.0)
        S_est, _ = cor.tail_fit_scatter((P - R) / n_safe, h, WATER_RADIUS, shape=shape,
                                        shared_axes=(0, 1), sensitivity=n_bins)
    S_counts = S_est * n_bins
    Att = cor.attenuation_factors(h, WATER_RADIUS)
    y = P[SLICES].sum(axis=0)
    mult = (n_bins * Att)[SLICES].sum(axis=0)
    add = (R + S_counts)[SLICES].sum(axis=0)

    dist = [np.hypot(xs - x, ys - yy) for _, x, yy in RODS]
    bg = (np.hypot(xs, ys) <= 60.0) & np.all([d > r + 12.0 for d, (r, _, _) in zip(dist, RODS)],
                                              axis=0)
    rod_roi = [d <= 0.5 * r for d, (r, _, _) in zip(dist, RODS)]

    def metrics(img):
        m = img[bg].mean()
        crc = [(img[roi].mean() / m - 1.0) / (CONTRAST - 1.0) for roi in rod_roi]
        return m, img[bg].std() / m, crc

    section("2. A phantom of hot rods: OSEM iteration by iteration")
    print(f"Lines at {radius:.0f} mm. Data: slices 20 to 74 summed, {y.sum():,.0f} prompts, of "
          f"which {T[SLICES].sum():,.0f} trues; the model's additive term (randoms from the "
          f"singles, scatter scaled to the tails) {add.sum():,.0f}. Image {N} x {N} pixels of "
          f"{PIXEL_MM:.0f} mm. Rods of radius 12, 8 and 5 mm at {CONTRAST:.0f} times the "
          f"background; their regions are the inner half radius. Background: {bg.sum()} pixels "
          "within 60 mm of the axis and 12 mm or more from a rod's edge.\n")
    print("| Iteration | Log-likelihood over iteration 1 | Background noise (CoV) | CRC 12 mm | "
          "CRC 8 mm | CRC 5 mm |")
    print("|---:|---:|---:|---:|---:|---:|")
    ll0 = mlem.log_likelihood(y, mlem.expected(np.ones((N, N)), A, mult, add))
    rows, images = {}, {}
    t0 = time.monotonic()

    def record(it, x):
        rows[it] = (mlem.log_likelihood(y, mlem.expected(x, A, mult, add)) - ll0, metrics(x))
        images[it] = x.copy()

    mlem.osem(y, A, mult, add, 32, n_subsets=SUBSETS, callback=record)
    osem_s = time.monotonic() - t0
    for it in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32):
        gain, (m, cov, crc) = rows[it]
        gain -= rows[1][0]
        print(f"| {it} | {gain:,.0f} | {pct(cov):.1f}% | " + " | ".join(f"{c:.2f}" for c in crc)
              + " |")
    print(f"\n32 iterations of {SUBSETS} subsets in {osem_s:.0f} s, with the likelihood and the "
          f"metrics at every iteration; the normalization read from the scans in {norm_s:.0f} s. "
          "CRC is the contrast recovery coefficient, (rod / background - 1) / (4 - 1): 1 is the "
          "true contrast.")

    # 2b. How certain is one realization's CRC?
    runs_b = ["phantom_b"] + [f"rodb{k}" for k in range(len(RODS))]
    P_b = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "prompts") for r in runs_b)
    R_b = sum(chain.randoms(work / r, h) for r in runs_b)
    with np.errstate(divide="ignore", invalid="ignore"):
        S_b, _ = cor.tail_fit_scatter((P_b - R_b) / n_safe, h, WATER_RADIUS, shape=shape,
                                      shared_axes=(0, 1), sensitivity=n_bins)
    y_b = P_b[SLICES].sum(axis=0)
    add_b = (R_b + S_b * n_bins)[SLICES].sum(axis=0)
    rows_b = {}
    mlem.osem(y_b, A, mult, add_b, 16, n_subsets=SUBSETS,
              callback=lambda it, x: rows_b.__setitem__(it, metrics(x)))
    T_b = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "trues") for r in runs_b)
    trues_only = {}
    for label, tt in (("a", T), ("b", T_b)):
        trues_only[label] = metrics(mlem.osem(tt[SLICES].sum(axis=0), A, mult, 0.0, 4,
                                              n_subsets=SUBSETS))[2]
    section("2b. How certain is one phantom's CRC?")
    print("A second, independent realization (b) of the same phantom, reconstructed the same way, "
          "and both realizations' trues alone (no randoms, no scatter, no estimate of either):\n")
    print("| Iteration | Realization | Background noise (CoV) | CRC 12 mm | CRC 8 mm | CRC 5 mm |")
    print("|---:|---|---:|---:|---:|---:|")
    for it in (4, 8, 16):
        for label, (m, cov, crc) in (("a", rows[it][1]), ("b", rows_b[it])):
            print(f"| {it} | {label} | {pct(cov):.1f}% | " + " | ".join(f"{c:.2f}" for c in crc)
                  + " |")
    for label in ("a", "b"):
        print(f"| 4 | {label}, trues only | | " + " | ".join(f"{c:.2f}" for c in trues_only[label])
              + " |")

    # 3. MLEM against OSEM.
    section("3. MLEM and OSEM: the same number of image updates")
    ll_m = {}
    mlem.osem(y, A, mult, add, 16, n_subsets=1, callback=lambda it, x: ll_m.__setitem__(
        it, (mlem.log_likelihood(y, mlem.expected(x, A, mult, add)) - ll0, metrics(x))))
    base = rows[1][0]
    print("| Image updates | MLEM iterations | OSEM iterations (8 subsets) | Log-likelihood over "
          "OSEM's iteration 1, MLEM | OSEM | CRC 12 mm, MLEM | OSEM |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for k in (1, 2):
        print(f"| {8 * k} | {8 * k} | {k} | {ll_m[8 * k][0] - base:,.0f} | "
              f"{rows[k][0] - base:,.0f} | {ll_m[8 * k][1][2][0]:.2f} | {rows[k][1][2][0]:.2f} |")
    print(f"| 1 | 1 | - | {ll_m[1][0] - base:,.0f} | | {ll_m[1][1][2][0]:.2f} | |")
    print("\nOne OSEM iteration projects and backprojects every view once, as one MLEM iteration "
          "does, at the same cost; the last row is that one MLEM iteration.")

    # 4. The corrections in the model.
    section("4. The background's profile with and without the corrections in the model")
    print("OSEM, 4 iterations of 8 subsets; the mean of the background over rings 10 mm wide, "
          "over the ring from 0 to 10 mm, and away from the rods (12 mm or more from an edge).\n")
    variants = [("all corrections", mult, add),
                ("the true randoms and scatter (the simulator's)", mult,
                 (R_true + S_true)[SLICES].sum(axis=0)),
                ("estimated randoms, true scatter", mult, (R + S_true)[SLICES].sum(axis=0)),
                ("no attenuation", n_bins[SLICES].sum(axis=0), add),
                ("no scatter", mult, R[SLICES].sum(axis=0)),
                ("no normalization", Att[SLICES].sum(axis=0), add),
                ("none", np.ones_like(y), np.zeros_like(y))]
    rings = [(0, 10), (20, 30), (40, 50), (60, 70)]
    away = np.all([d > r + 12.0 for d, (r, _, _) in zip(dist, RODS)], axis=0)
    print("| Model | " + " | ".join(f"{a} to {b} mm" for a, b in rings) + " | CRC 12 mm |")
    print("|---|" + "---:|" * (len(rings) + 1))
    for label, mu, ad in variants:
        img = mlem.osem(y, A, mu, ad, 4, n_subsets=SUBSETS)
        rr = np.hypot(xs, ys)
        means = [img[(rr >= a) & (rr < b) & away].mean() for a, b in rings]
        ref = np.mean(means)
        print(f"| {label} | " + " | ".join(f"{v / ref:.3f}" for v in means)
              + f" | {metrics(img)[2][0]:.2f} |")
    print("\nEach ring's mean over the mean of the four rings: a correct model gives 1.000 in "
          "each.")

    # 5. Post-filter.
    section("5. A post-filter: noise against contrast")
    print("| Image | Background noise (CoV) | CRC 12 mm | CRC 8 mm | CRC 5 mm |")
    print("|---|---:|---:|---:|---:|")
    for it in (4, 32):
        for f in (0.0, 4.0, 6.0):
            img = images[it] if f == 0 else gaussian_filter(images[it], f, PIXEL_MM)
            _, cov, crc = metrics(img)
            label = f"iteration {it}" + (f", Gaussian {f:.0f} mm FWHM" if f else "")
            print(f"| {label} | {pct(cov):.1f}% | " + " | ".join(f"{c:.2f}" for c in crc) + " |")
    np.save(work / "osem_it4.npy", images[4])
    np.save(work / "osem_it32.npy", images[32])
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
