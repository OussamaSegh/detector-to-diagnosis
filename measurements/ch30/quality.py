#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 30 measurements: image quality of MiniDAQ's reconstructions, after the methods of NEMA
NU 2 in 2D.

The scanner, the normalization, the background and the hot rods are those of measurements/ch28
(given the same WORK_DIR, its runs are reused); the lines are at 156 mm, as ch28 found.

1. Spatial resolution, NEMA's way: point sources in air at 10, 50 and 100 mm from the axis,
   reconstructed by FBP; the radial and tangential FWHM and FWTM, and what the pixel size does.
2. The same points by OSEM: the width against the iteration.
3. Contrast and background variability of the hot rods: OSEM iterations and post-filters.
4. Repeatability: six independent realizations of the phantom, one protocol.
5. What the region of interest's definition does to the contrast.

    MINIDAQ_RECON_CPP=build/release/recon python3 measurements/ch30/quality.py \
        build/release/minidaq/apps [WORK_DIR] > measurements/ch30/quality.txt
"""
import importlib.util
import os
import pathlib
import platform
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import chain, corrections as cor, fbp, mlem, project, quality as q  # noqa: E402
from tools.recon import sinogram as sg  # noqa: E402

_spec = importlib.util.spec_from_file_location("ch28", ROOT / "measurements/ch28/reconstruct.py")
ch28 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch28)  # its simulation, phantom and filter; it reads sys.argv[1] too

RADIUS = 156.0
POINTS_X = (10.0, 10.64, 50.0, 100.0)  # 10.64: half a bin (0.64 mm) further out
WARM_X = (10.0, 50.0)  # points in the water, on the background's activity
REALIZATIONS = 6
SUBSETS = ch28.SUBSETS
RODS, CONTRAST = ch28.RODS, ch28.CONTRAST
PROTOCOL = (4, 4.0)  # OSEM iterations, Gaussian post-filter FWHM in mm


def section(title):
    print(f"\n## {title}\n")


def runs_of(m):
    """The four runs (background and three rods) of realization m: ch28's a and b, then ours."""
    if m == 0:
        return ["phantom"] + [f"rod{k}" for k in range(3)]
    if m == 1:
        return ["phantom_b"] + [f"rodb{k}" for k in range(3)]
    return [f"phantom_r{m}"] + [f"rod_r{m}_{k}" for k in range(3)]


def simulate_all(work):
    jobs = [(f"norm{k}", ch28.NORM, k) for k in range(1, ch28.NORM_RUNS + 1)]
    jobs += [("scatter_model", ch28.PHANTOM, 2000, [])]
    jobs += [("phantom", ch28.PHANTOM, 1000), ("phantom_b", ch28.PHANTOM, 1001)]
    jobs += [(f"rod{k}", ch28.rod_args(*r), 4001 + k) for k, r in enumerate(RODS)]
    jobs += [(f"rodb{k}", ch28.rod_args(*r), 4101 + k) for k, r in enumerate(RODS)]
    for m in range(2, REALIZATIONS):
        jobs.append((f"phantom_r{m}", ch28.PHANTOM, 1000 + m))
        jobs += [(f"rod_r{m}_{k}", ch28.rod_args(*r), 4001 + 100 * m + k)
                 for k, r in enumerate(RODS)]
    for x in POINTS_X:
        jobs.append((f"point_x{x:g}", ["--source", "point", "--centre", f"{x:g},0,0",
                                        "--phantom", "0", "--activity", "1e6", "--seconds", "2"],
                     6000 + int(round(100 * x))))
    for x in WARM_X:
        jobs.append((f"wpoint_x{x:g}", ["--source", "point", "--centre", f"{x:g},0,0",
                                        "--activity", "2e6", "--seconds", "5"], 7000 + int(x)))
    with ThreadPoolExecutor(max(1, min(4, os.cpu_count() or 1))) as ex:
        return sum(ex.map(lambda j: ch28.simulate(work, *j), jobs))


def main():
    work_arg = sys.argv[2] if len(sys.argv) > 2 else None
    tmp = None if work_arg else tempfile.TemporaryDirectory()
    work = pathlib.Path(work_arg or tmp.name)
    work.mkdir(parents=True, exist_ok=True)
    try:
        project.load_cpp()
        Proj = project.CppProjector
        which = "the C++ projector (Chapter 29)"
    except ImportError:
        Proj = project.Projector
        which = "the numpy projector (recon_cpp is not built: slow)"
    print("# Chapter 30: image quality, after NEMA NU 2 in 2D\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}; {which}.")
    t0 = time.monotonic()
    sim_s = simulate_all(work)
    print(f"Simulated in {sim_s:.0f} s of CPU time (0 if the runs were reused).")
    n_bins, geo, _ = chain.normalization([work / f"norm{k}" for k in range(1, ch28.NORM_RUNS + 1)],
                                         118.0)

    # 1. Resolution by FBP.
    section("1. Spatial resolution: point sources in air, FBP")
    widths = {}
    point = {}
    for x in POINTS_X:
        d = work / f"point_x{x:g}"
        hp = sg.read_header(d / "truth.hdr")
        y = sg.read(hp, "prompts").sum(axis=0)
        r = chain.randoms(d, hp).sum(axis=0)
        m = n_bins.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            corrected = np.where(m > 0, (y - r) / np.where(m > 0, m, 1.0), 0.0)
        point[x] = (hp, y, r, m, corrected)
    print("| Point at | Pixel | Radial FWHM | Radial FWTM | Tangential FWHM | Tangential FWTM | "
          "Peak at x |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for x in POINTS_X:
        hp, *_, corrected = point[x]
        for pixel in (0.25, 0.5, 1.0, 2.0):
            n = int(round(256.0 / pixel))
            img = fbp.fbp(corrected, hp, RADIUS, n=n, pixel_mm=pixel, projector=Proj)
            radial, tangential = q.point_profiles(img, half_band=max(1, int(round(2.0 / pixel))))
            w = [q.width(radial, pixel), q.width(radial, pixel, 0.1),
                 q.width(tangential, pixel), q.width(tangential, pixel, 0.1)]
            peak = (q.parabolic_peak(radial)[0] - (n - 1) / 2.0) * pixel
            widths[(x, pixel)] = w
            print(f"| {x:g} mm | {pixel:g} mm | " + " | ".join(f"{v:.2f} mm" for v in w)
                  + f" | {peak:.2f} mm |")
    print("\nFBP with the ramp filter unwindowed, the data corrected for randoms (from the singles) "
          "and normalization; all slices summed. Each profile is summed over a band 4 to 6 mm "
          "across (the brightest pixel and round(2 mm / pixel) on each side); the peak by a "
          "parabola through three samples, each side by linear interpolation. Peak at x: the "
          "parabola's vertex on the radial profile.")

    # 2. The same points by OSEM.
    section("2. The same points by OSEM, iteration by iteration")
    its = (1, 2, 4, 8, 16, 32)
    print("| Point at | Width | " + " | ".join(f"Iteration {i}" for i in its) + " | FBP |")
    print("|---:|---|" + "---:|" * (len(its) + 1))
    pixel = 0.5
    n = 512
    for x in POINTS_X:
        hp, y, r, m, _ = point[x]
        s, phi = project.bin_lines(hp, RADIUS)
        A = Proj(s, phi, n=n, pixel_mm=pixel)
        rows = {}

        def record(it, img):
            if it in its:
                rad, tan = q.point_profiles(img, half_band=4)
                rows[it] = (q.width(rad, pixel), q.width(tan, pixel))

        mlem.osem(y, A, m, r, its[-1], n_subsets=SUBSETS, callback=record)
        fb = widths[(x, pixel)]
        print(f"| {x:g} mm | radial FWHM | " + " | ".join(f"{rows[i][0]:.2f}" for i in its)
              + f" | {fb[0]:.2f} |")
        print(f"| {x:g} mm | tangential FWHM | " + " | ".join(f"{rows[i][1]:.2f}" for i in its)
              + f" | {fb[2]:.2f} |")
    print(f"\nWidths in mm. OSEM with {SUBSETS} subsets, randoms and normalization in the model, "
          f"{pixel} mm pixels; FBP from section 1 at the same pixel size.")

    # The phantom: corrections for every realization.
    h = sg.read_header(work / "phantom" / "truth.hdr")
    shape = chain.scatter_shape(work / "scatter_model", geo)
    Att = cor.attenuation_factors(h, ch28.WATER_RADIUS)
    n_safe = np.where(n_bins > 0, n_bins, 1.0)
    mult_3d = n_bins * Att

    def data(runs):
        P = sum(sg.read(sg.read_header(work / r / "truth.hdr"), "prompts") for r in runs)
        R = sum(chain.randoms(work / r, h) for r in runs)
        with np.errstate(divide="ignore", invalid="ignore"):
            S, _ = cor.tail_fit_scatter((P - R) / n_safe, h, ch28.WATER_RADIUS, shape=shape,
                                        shared_axes=(0, 1), sensitivity=n_bins)
        return P[ch28.SLICES].sum(axis=0), (R + S * n_bins)[ch28.SLICES].sum(axis=0)

    # 2b. Points on a warm background.
    section("2b. Points in the water, on the background's activity")
    s, phi = project.bin_lines(h, RADIUS)
    A = Proj(s, phi, n=n, pixel_mm=pixel)
    xs, ys = A.pixel_centers()
    mult = mult_3d[ch28.SLICES].sum(axis=0)
    its_w = (1, 2, 4, 8, 16, 32)
    print("| Point at | Width | " + " | ".join(f"Iteration {i}" for i in its_w) + " |")
    print("|---:|---|" + "---:|" * len(its_w))
    for x in WARM_X:
        y, add = data(["phantom", f"wpoint_x{x:g}"])
        ring = (np.hypot(xs - x, ys) >= 10.0) & (np.hypot(xs - x, ys) <= 20.0)
        near = np.hypot(xs - x, ys) <= 5.0
        rows = {}

        def record(it, img):
            if it in its_w:
                sub = np.where(near, img - img[ring].mean(), 0.0)
                rad, tan = q.point_profiles(sub, half_band=4)
                rows[it] = (q.width(rad, pixel), q.width(tan, pixel))

        mlem.osem(y, A, mult, add, its_w[-1], n_subsets=SUBSETS, callback=record)
        print(f"| {x:g} mm | radial FWHM | " + " | ".join(f"{rows[i][0]:.2f}" for i in its_w)
              + " |")
        print(f"| {x:g} mm | tangential FWHM | " + " | ".join(f"{rows[i][1]:.2f}" for i in its_w)
              + " |")
    print(f"\nA point of 2 MBq for 5 s in the water, added to the background's run (20 MBq in the "
          f"cylinder); all corrections in the model, {pixel} mm pixels. The background is the mean "
          "over the ring 10 to 20 mm from the point, subtracted within 5 mm of it before the "
          "profiles are taken.")

    # The phantom of hot rods.
    A = Proj(s, phi, n=ch28.N, pixel_mm=ch28.PIXEL_MM)
    xs, ys = A.pixel_centers()

    # The regions of the largest size: their edges 8 mm or more from a rod's edge and 10 mm from
    # the cylinder's; 22 mm apart, so that two 12 mm regions overlap by 2 mm at most.
    keep_out = [(x, yy, rad + 12.0 + 8.0) for rad, x, yy in RODS]
    centers = q.place_background_rois(12, keep_out, inside_mm=70.0, radius_mm=12.0,
                                      spacing_mm=22.0)

    def figures(img):
        """CRC of each rod (region: the rod) and the background variability for each rod's size."""
        crc, bv = [], []
        for rad, x, yy in RODS:
            bg_mean, var = q.background_variability(img, xs, ys, centers, rad)
            hot = img[q.disc(xs, ys, x, yy, rad)].mean()
            crc.append(q.contrast_recovery(hot, bg_mean, CONTRAST))
            bv.append(var)
        return crc, bv

    def filtered(img, f):
        return img if f == 0 else ch28.gaussian_filter(img, f, ch28.PIXEL_MM)

    # 3. Contrast and background variability.
    section("3. Contrast and background variability of the hot rods")
    print("Twelve background regions, for each rod size a circle of the rod's radius at each "
          "center; the 12 mm regions 8 mm or more from a rod's edge, inside 70 mm of the axis and "
          "22 mm apart: " +
          ", ".join(f"({cx:.0f}, {cy:.0f})" for cx, cy in centers) + " mm. Each rod's region is "
          "the rod.\n")
    y, add = data(runs_of(0))
    images = {}
    mlem.osem(y, A, mult, add, 16, n_subsets=SUBSETS,
              callback=lambda it, x: images.__setitem__(it, x.copy()))
    print("| Image | CRC 12 mm | 8 mm | 5 mm | Variability 12 mm | 8 mm | 5 mm |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for it in (2, 4, 8, 16):
        for f in (0.0, 4.0, 6.0):
            crc, bv = figures(filtered(images[it], f))
            label = f"iteration {it}" + (f", {f:.0f} mm filter" if f else "")
            print(f"| {label} | " + " | ".join(f"{c:.2f}" for c in crc) + " | "
                  + " | ".join(f"{100 * b:.1f}%" for b in bv) + " |")

    # 4. Repeatability.
    section("4. Repeatability: six realizations, one protocol")
    it_p, f_p = PROTOCOL
    results = []
    protocol_images = []
    for m in range(REALIZATIONS):
        y, add = data(runs_of(m))
        img = filtered(mlem.osem(y, A, mult, add, it_p, n_subsets=SUBSETS), f_p)
        protocol_images.append(img)
        results.append(figures(img))
    print(f"OSEM, {it_p} iterations of {SUBSETS} subsets, Gaussian {f_p:.0f} mm FWHM.\n")
    print("| Realization | CRC 12 mm | 8 mm | 5 mm | Variability 12 mm | 8 mm | 5 mm |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for m, (crc, bv) in enumerate(results):
        print(f"| {m + 1} | " + " | ".join(f"{c:.3f}" for c in crc) + " | "
              + " | ".join(f"{100 * b:.1f}%" for b in bv) + " |")
    crc = np.array([r[0] for r in results])
    bv = np.array([r[1] for r in results])
    for label, fn in (("mean", np.mean), ("SD", lambda a, axis: np.std(a, axis=axis, ddof=1))):
        print(f"| {label} | " + " | ".join(f"{v:.3f}" for v in fn(crc, axis=0)) + " | "
              + " | ".join(f"{100 * v:.1f}%" for v in fn(bv, axis=0)) + " |")

    # 5. The region's definition.
    section("5. The region of interest decides the number")
    img = protocol_images[0]
    print("Realization 1, the protocol of section 4; each rod's background as in sections 3 and "
          "4, from the regions of its size.\n")

    def background(im, rad):
        return q.background_variability(im, xs, ys, centers, rad)[0]

    variants = [("the rod (radius r)", lambda x, yy, rad: q.disc(xs, ys, x, yy, rad)),
                ("its inner half (r / 2)", lambda x, yy, rad: q.disc(xs, ys, x, yy, 0.5 * rad)),
                ("the rod, 2 mm off", lambda x, yy, rad: q.disc(xs, ys, x + 2.0, yy, rad)),
                ("the rod, 4 mm off", lambda x, yy, rad: q.disc(xs, ys, x + 4.0, yy, rad))]
    print("| Region | CRC 12 mm | 8 mm | 5 mm |")
    print("|---|---:|---:|---:|")
    for label, mask in variants:
        vals = [q.contrast_recovery(img[mask(x, yy, rad)].mean(), background(img, rad), CONTRAST)
                for rad, x, yy in RODS]
        print(f"| {label} | " + " | ".join(f"{v:.2f}" for v in vals) + " |")
    maxes = [[q.contrast_recovery(im[q.disc(xs, ys, x, yy, rad)].max(), background(im, rad),
                                  CONTRAST) for rad, x, yy in RODS] for im in protocol_images]
    print("| its hottest pixel | " + " | ".join(f"{v:.2f}" for v in maxes[0]) + " |")
    mx = np.array(maxes)
    print(f"\nOver the six realizations the hottest pixel's CRC has a SD of "
          + ", ".join(f"{v:.3f}" for v in mx.std(axis=0, ddof=1)) + " (12, 8, 5 mm), against "
          + ", ".join(f"{v:.3f}" for v in crc.std(axis=0, ddof=1)) + " for the mean over the rod.")
    print(f"\nReconstructions and analysis: {time.monotonic() - t0:.0f} s.")
    if tmp:
        tmp.cleanup()


if __name__ == "__main__":
    main()
