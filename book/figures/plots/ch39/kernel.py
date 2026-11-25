# SPDX-License-Identifier: MIT
"""Figure for Chapter 39: what one count puts into the image, with and without time of flight. One
count in one bin (a line 30 degrees from the horizontal, 20 mm from the axis, its TOF bin 40 mm from
the line's middle) is backprojected with the chapter's projectors (tools/recon/project.py): without
TOF it spreads along the whole line; with TOF it is weighted by the kernel, a Gaussian along the line
whose width is set by the coincidence time resolution (CTR), shown at 600, 300 and 150 ps FWHM.
TOF bins of 50 ps, so that the bin's width does not hide the kernel's.

    python3 book/tools/figures.py build book/figures/plots/ch39/kernel.py screen 10 pdf tools/recon/project.py
"""
import pathlib
import sys

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.recon import project  # noqa: E402

TOF_BINS = 41
BIN_PS = 50.0
ALONG_MM = 40.0


def main(dst):
    phi = np.array([[np.radians(120.0)]])  # the line's normal; the line runs at 30 degrees
    s = np.array([[20.0]])
    plain = project.Projector(s, phi, n=128, pixel_mm=2.0)
    panels = [("without TOF: the whole line", plain.back(np.ones((1, 1))))]
    centers = project.tof_bins_mm(TOF_BINS, BIN_PS)
    k = int(np.argmin(np.abs(centers - ALONG_MM)))
    for ctr in (600.0, 300.0, 150.0):
        tof = project.TofProjector(s, phi, n=128, pixel_mm=2.0, tof_bins=TOF_BINS, tof_bin_ps=BIN_PS,
                                   ctr_fwhm_ps=ctr)
        y = np.zeros((1, 1, TOF_BINS))
        y[0, 0, k] = 1.0
        fwhm_mm = ctr * project.C_MM_PER_PS / 2.0
        panels.append((f"CTR {ctr:.0f} ps: {fwhm_mm:.0f} mm FWHM", tof.back(y)))
    fig, axes = d2d.figure(height=1.75, width=1.0, ncols=4)
    xs, ys = plain.pixel_centers()
    for ax, (title, img) in zip(axes, panels):
        ax.imshow(img, cmap=d2d.CMAP, vmin=0, vmax=img.max(), interpolation="nearest", origin="lower",
                  extent=(xs.min() - 1, xs.max() + 1, ys.min() - 1, ys.max() + 1))
        ax.add_patch(__import__("matplotlib").patches.Circle((0, 0), 120, fill=False, ec="white",
                                                              lw=0.6, ls=":"))
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(title, fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, pad=2)
    fig.tight_layout(pad=0.2, w_pad=0.3)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
