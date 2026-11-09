# SPDX-License-Identifier: MIT
"""Figure for Chapter 33: the image at the end of the chain, the phantom acquisition reconstructed by
OSEM (C++ projector, 4 iterations of 8 subsets, 128 x 128 pixels of 2 mm), from
measurements/ch33/e2e/image.npy, with its horizontal and vertical profiles through the centre.

    python3 book/tools/figures.py build book/figures/plots/ch33/image.py screen 8 pdf measurements/ch33/e2e/image.npy
"""
import pathlib
import sys

import numpy as np

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch33/e2e/image.npy"


def main(dst):
    img = np.load(SRC)
    n = img.shape[0]
    c = (np.arange(n) - (n - 1) / 2) * 2.0
    fig, (ax, bx) = d2d.figure(height=2.2, width=1.0, ncols=2, gridspec_kw={"width_ratios": [1, 1.5]})
    ax.imshow(img, cmap="magma", extent=(c[0] - 1, c[-1] + 1, c[0] - 1, c[-1] + 1), origin="lower", interpolation="nearest",
              vmax=np.percentile(img, 99.5))
    t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(80 * np.cos(t), 80 * np.sin(t), color="white", lw=0.6, ls=":")
    ax.set_xticks([-100, 0, 100])
    ax.set_yticks([-100, 0, 100])
    ax.set_xlabel("x, mm")
    ax.set_ylabel("y, mm")
    ax.grid(False)
    band = slice(n // 2 - 2, n // 2 + 2)
    mean_in = img[np.hypot(*np.meshgrid(c, c)) < 60].mean()
    bx.plot(c, img[band].mean(axis=0) / mean_in, color=d2d.PART, lw=d2d.LINE_PT * 1.3, label="horizontal, 8 mm band")
    bx.plot(c, img[:, band].mean(axis=1) / mean_in, color=d2d.CAT[0], lw=d2d.LINE_PT, ls="--", label="vertical, 8 mm band")
    for x in (-80, 80):
        bx.axvline(x, color=d2d.MUTED, lw=0.6, ls=":")
    bx.text(0, 0.12, "the activity's edge at 80 mm (dotted)", ha="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED)
    bx.set_xlabel("position, mm")
    bx.set_ylabel("over the mean inside 60 mm")
    bx.set_ylim(0, 2.3)
    bx.legend(loc="upper center", ncol=2, fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
