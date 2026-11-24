# SPDX-License-Identifier: MIT
"""Figure for Chapter 28: what "smear it back across the image, add the views" looks like. A phantom
of one hot rod and one small point, forward-projected with the chapter's projector (tools/recon) over
MiniDAQ's 192 views, no noise; then backprojected from 1, 4 and 16 evenly spaced views and from all
192, without a filter; and last, all 192 views with each view ramp-filtered first: filtered
backprojection. The star of a few views and the 1/r blur of the unfiltered sum are what the ramp
filter removes.

    python3 book/tools/figures.py build book/figures/plots/ch28/backprojection.py screen 6 pdf tools/recon/project.py
"""
import pathlib
import sys
from types import SimpleNamespace

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.recon import project  # noqa: E402

N_VIEWS = 192


def phantom(xs, ys):
    img = np.zeros_like(xs)
    img[np.hypot(xs - 30, ys - 20) <= 10] = 1.0   # a hot rod, 20 mm across
    img[np.hypot(xs + 35, ys + 30) <= 3] = 4.0    # a small point
    return img


def ramp(sino):
    """Each view filtered with |frequency| (Ram-Lak), zero-padded against wrap-around."""
    n = sino.shape[1]
    pad = 2 ** int(np.ceil(np.log2(2 * n)))
    f = np.abs(np.fft.fftfreq(pad))
    out = np.fft.ifft(np.fft.fft(sino, pad, axis=1) * f, axis=1).real
    return out[:, :n]


def main(dst):
    first = -104
    header = SimpleNamespace(r=np.arange(first, -first + 1), views=N_VIEWS)
    s, phi = project.bin_lines(header)
    proj = project.Projector(s, phi, n=128, pixel_mm=2.0)
    xs, ys = proj.pixel_centers()
    truth = phantom(xs, ys)
    sino = proj.forward(truth)
    panels = [("the object", truth)]
    for k in (1, 4, 16, N_VIEWS):
        views = list(range(0, N_VIEWS, N_VIEWS // k))
        panels.append((f"{k} view{'s' if k > 1 else ''}, summed", proj.back(sino[views], views)))
    panels.append(("192 views, ramp-filtered", proj.back(ramp(sino))))
    fig, axes = d2d.figure(height=1.45, width=1.0, ncols=6)
    for ax, (title, img) in zip(axes, panels):
        crop = img[24:104, 24:104]
        ax.imshow(crop, cmap=d2d.CMAP, vmin=0.0, vmax=crop.max(), interpolation="nearest", origin="lower")
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_title(title, fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, pad=2)
    fig.tight_layout(pad=0.2, w_pad=0.25)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
