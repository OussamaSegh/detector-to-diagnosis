#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 29 measurements: the C++ projector against the numpy one.

1. Agreement: forward and back of random data on MiniDAQ's 2D geometry (192 views, 227 bins,
   lines at 156 mm, 128 x 128 pixels of 2 mm), and an OSEM image.
2. Time: forward and back, the median of 7 runs, numpy and C++ with 1, 2 and 4 threads; the
   numpy projector's set-up (its weights) and its memory.
3. Time of a whole reconstruction: 4 iterations of 8 subsets, numpy and C++ with 4 threads.

    MINIDAQ_RECON_CPP=build/release/recon python3 measurements/ch29/projector.py \
        > measurements/ch29/projector.txt

Use the release build's module: the debug build is unoptimized.
"""
import os
import pathlib
import platform
import statistics
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import mlem, project, sinogram as sg  # noqa: E402


def median_time(f, runs=7):
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        f()
        times.append(time.perf_counter() - t)
    return statistics.median(times)


def main():
    h = sg.Header(path=None, radial_bins=227, views=192, slices=1, tof_bins=1, first_r=-113,
                  max_ring_difference=0, fov_radius_mm=120.0, files={})
    s, phi = project.bin_lines(h, radius_mm=156.0)
    print("# Chapter 29: the C++ projector against the numpy projector\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}. Module: "
          f"{os.environ.get('MINIDAQ_RECON_CPP', '(sys.path)')}.\n")
    t = time.perf_counter()
    py = project.Projector(s, phi, n=128, pixel_mm=2.0)
    setup = time.perf_counter() - t
    weights = sum(i.nbytes + w.nbytes for i, w in py._views)
    cc = {k: project.CppProjector(s, phi, n=128, pixel_mm=2.0, threads=k) for k in (1, 2, 4)}

    print("## 1. Agreement\n")
    rng = np.random.default_rng(29)
    x = rng.random((128, 128))
    y = rng.random(s.shape)
    fa, fb = py.forward(x), cc[4].forward(x)
    ba, bb = py.back(y), cc[4].back(y)
    print("| Quantity | Largest difference, relative to the largest value |")
    print("|---|---:|")
    print(f"| forward, random image | {np.abs(fa - fb).max() / np.abs(fa).max():.1e} |")
    print(f"| back, random sinogram | {np.abs(ba - bb).max() / np.abs(ba).max():.1e} |")
    print(f"| back, 1 thread against 4 | "
          f"{np.abs(cc[1].back(y) - bb).max() / np.abs(bb).max():.1e} |")
    xs, ys = py.pixel_centers()
    truth = ((xs ** 2 + ys ** 2) <= 80.0 ** 2) * 1.0 + ((xs - 30) ** 2 + ys ** 2 <= 100) * 3.0
    mult = rng.uniform(0.5, 1.0, s.shape)
    counts = rng.poisson(mlem.expected(truth, py, mult, 0.3)).astype(float)
    ia = mlem.osem(counts, py, mult, 0.3, 4, n_subsets=8)
    ib = mlem.osem(counts, cc[4], mult, 0.3, 4, n_subsets=8)
    print(f"| OSEM image, 4 iterations of 8 subsets | {np.abs(ia - ib).max() / ia.max():.1e} |")
    print("\nThe numpy projector keeps its weights in float32 (about 7 significant digits); "
          "the C++ one computes them in double for every line.\n")

    print("## 2. Time of one projection (median of 7)\n")
    print("| Projector | Forward | Back |")
    print("|---|---:|---:|")
    print(f"| numpy | {median_time(lambda: py.forward(x)) * 1e3:.1f} ms | "
          f"{median_time(lambda: py.back(y)) * 1e3:.1f} ms |")
    for k, p in cc.items():
        print(f"| C++, {k} thread{'s' if k > 1 else ''} | "
              f"{median_time(lambda p=p: p.forward(x)) * 1e3:.1f} ms | "
              f"{median_time(lambda p=p: p.back(y)) * 1e3:.1f} ms |")
    print(f"\nThe numpy projector computes its weights once, in {setup:.2f} s, and keeps them: "
          f"{weights / 1e6:.0f} MB. The C++ one computes them for every line, every time, and "
          "keeps only the lines.\n")

    print("## 3. Time of a reconstruction: 4 iterations of 8 subsets\n")
    print("| Projector | Time |")
    print("|---|---:|")
    for label, p in (("numpy", py), ("C++, 4 threads", cc[4])):
        seconds = median_time(lambda p=p: mlem.osem(counts, p, mult, 0.3, 4, n_subsets=8), 3)
        print(f"| {label} | {seconds:.2f} s |")


if __name__ == "__main__":
    main()
