# SPDX-License-Identifier: MIT
"""Figure for Chapter 12: sinograms histogrammed from MiniDAQ list-mode files
(measurements/ch12/sinogram.py). Left: a point source at (40, -25) mm draws one
sinusoid. Middle: a uniform cylinder (radius 80 mm, length 100 mm) in water
(radius 100 mm). Right: the cylinder's Michelogram, prompts by the rings of the
two crystals.

    python3 book/tools/figures/ch12_sinogram.py book/src/img/ch12-sinogram.png
"""
import math
import os
import struct
import sys
import zlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "../../../measurements/ch12/sino")
VIEWS, RADIAL, MAX_R, N, R_MM, RINGS = 192, 227, 113, 384, 150.0, 48


def load(name, suffix, fmt):
    with open(os.path.join(SRC, f"{name}.{suffix}.z"), "rb") as f:
        data = zlib.decompress(f.read())
    return list(struct.unpack(f"<{len(data) // struct.calcsize(fmt)}{fmt}", data))


def plane(values, rows, cols):
    return [values[i * cols:(i + 1) * cols] for i in range(rows)]


def main(dst):
    fig, axes = plt.subplots(1, 3, figsize=(6.4, 2.6), dpi=300,
                             gridspec_kw={"width_ratios": [1, 1, 0.95]})
    # Radial bins are not evenly spaced: label the axis with positions in mm.
    ticks_mm = [-100, -50, 0, 50, 100]
    ticks_bin = [-N / math.pi * math.asin(-s / R_MM) + MAX_R for s in ticks_mm]
    for ax, name, title in ((axes[0], "point", "point source"), (axes[1], "cylinder", "water cylinder")):
        img = plane(load(name, "prompts2d.u32", "I"), VIEWS, RADIAL)
        ax.imshow(img, aspect="auto", cmap="gray_r", interpolation="nearest",
                  extent=(-0.5, RADIAL - 0.5, VIEWS - 0.5, -0.5))
        ax.set_xticks(ticks_bin)
        ax.set_xticklabels([str(t) for t in ticks_mm], fontsize=6.5)
        ax.set_yticks([0, 48, 96, 144, 191])
        ax.set_yticklabels(["0", "45", "90", "135", "180"], fontsize=6.5)
        ax.set_xlabel("radial position s (mm)", fontsize=7.5)
        ax.set_title(title, fontsize=8.5)
    axes[0].set_ylabel("view angle (degrees)", fontsize=7.5)
    m = plane(load("cylinder", "michelogram.u64", "Q"), RINGS, RINGS)
    shown = [[math.log10(v) if v > 0 else float("nan") for v in row] for row in m]
    im = axes[2].imshow(shown, origin="lower", cmap="viridis", interpolation="nearest")
    axes[2].set_xlabel("ring of crystal b", fontsize=7.5)
    axes[2].set_ylabel("ring of crystal a", fontsize=7.5)
    axes[2].set_title("Michelogram (cylinder)", fontsize=8.5)
    axes[2].tick_params(labelsize=6.5)
    cb = fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
    cb.set_label("log10 prompts", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ch12-sinogram.png")
