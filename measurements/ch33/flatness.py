#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 33 measurements: what the end-to-end image checks see, with and without the
attenuation correction, over several seeds.

The phantom of tools/e2e.py (an 80 mm cylinder of activity in a 90 mm water cylinder, 5 MBq for
2 s) is simulated offline by minidaq_sim --link 1, which writes the records the server writes from
the same singles (SRS-SYS-006), binned, and reconstructed as tools/e2e.py does: OSEM, 4 iterations
of 8 subsets, 128 x 128 pixels of 2 mm, randoms from the singles; once with the attenuation of the
water cylinder in the model and once without.

    MINIDAQ_RECON_CPP=build/release/recon python3 measurements/ch33/flatness.py \
        build/release/minidaq/apps > measurements/ch33/flatness.txt
"""
import os
import pathlib
import platform
import subprocess
import sys
import tempfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import e2e  # noqa: E402
from tools.recon import chain, corrections as cor, mlem, project, sinogram as sg  # noqa: E402

SEEDS = (33, 34, 35, 36, 37)


def image_metrics(img, xs, ys, pixel_mm=2.0):
    r = np.hypot(xs, ys)
    edges = np.arange(0.0, 120.0 + pixel_mm, pixel_mm)
    ring = np.digitize(r, edges) - 1
    profile = np.array([img[ring == k].mean() for k in range(len(edges) - 1)])
    centers = 0.5 * (edges[:-1] + edges[1:])
    level = 0.5 * img[r < 48.0].mean()
    k = int(np.argmax((profile < level) & (centers > 40.0)))
    r_half = centers[k - 1] + (profile[k - 1] - level) / (profile[k - 1] - profile[k]) * pixel_mm
    ratio = img[r < 24.0].mean() / img[(r >= 24.0) & (r < 48.0)].mean()
    return r_half, ratio


def main():
    apps = pathlib.Path(sys.argv[1])
    print("# Chapter 33: the end-to-end image checks with and without attenuation correction\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs; numpy {np.__version__}.\n")
    print("| Seed | Prompts binned | Radius, AC | Center/periphery, AC | Radius, no AC | "
          "Center/periphery, no AC |")
    print("|---:|---:|---:|---:|---:|---:|")
    rows = []
    for seed in SEEDS:
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            subprocess.run([apps / "minidaq_sim", "--activity", "5e6", "--seconds", "2",
                            "--source", "cylinder", "--phantom", "90", "--seed", str(seed),
                            "--link", "1", "--listmode", d], check=True, capture_output=True)
            files = sorted(d.glob("*.mdql"))
            subprocess.run([apps / "minidaq_listmode", "sino", "--out", d / "sino", *files],
                           check=True, capture_output=True)
            h = sg.read_header(d / "sino.hdr")
            y = sg.read(h, "prompts").sum(axis=0)
            r = chain.randoms(d, h).sum(axis=0)
            s, phi = project.bin_lines(h, e2e.LOR_RADIUS_MM)
            proj = project.CppProjector(s, phi, n=128, pixel_mm=2.0)
            xs, ys = proj.pixel_centers()
            att = cor.attenuation_factors(h, e2e.PHANTOM_MM).sum(axis=0)
            flat = np.full_like(y, float(h.shape[0]))  # the slices summed, no attenuation
            with_ac = image_metrics(mlem.osem(y, proj, att, r, 4, n_subsets=8), xs, ys)
            without = image_metrics(mlem.osem(y, proj, flat, r, 4, n_subsets=8), xs, ys)
            rows.append((with_ac, without))
            print(f"| {seed} | {int(y.sum()):,} | {with_ac[0]:.2f} mm | {with_ac[1]:.3f} | "
                  f"{without[0]:.2f} mm | {without[1]:.3f} |")
    a = np.array([[w[0][0], w[0][1], w[1][0], w[1][1]] for w in rows])
    print(f"\nWith AC: radius {a[:, 0].min():.2f} to {a[:, 0].max():.2f} mm, center/periphery "
          f"{a[:, 1].min():.3f} to {a[:, 1].max():.3f}. Without: radius {a[:, 2].min():.2f} to "
          f"{a[:, 2].max():.2f} mm, center/periphery {a[:, 3].min():.3f} to {a[:, 3].max():.3f}.")
    print(f"The checks of tools/e2e.py: radius within {e2e.RADIUS_TOLERANCE_MM:g} mm of "
          f"{e2e.ACTIVE_RADIUS_MM:g} mm, center/periphery within {e2e.FLATNESS_TOLERANCE:g} of 1.")


if __name__ == "__main__":
    main()
