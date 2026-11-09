# SPDX-License-Identifier: MIT
"""Figure for Chapter 28: a phantom of hot rods, its sinogram and its OSEM reconstruction at six
iterations, made with the chapter's own tool (tools/recon: Joseph's projector, osem()) on data
simulated here in numpy: the phantom forward-projected over MiniDAQ's 192 views, a uniform additive
term for randoms and scatter, and Poisson noise with a fixed seed, at about the measurement's counts.

    python3 book/tools/figures.py build book/figures/plots/ch28/montage.py screen 6 pdf tools/recon/mlem.py
"""
import pathlib
import sys
from types import SimpleNamespace

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.recon import mlem, project  # noqa: E402

SHOW = [1, 2, 4, 8, 16, 32]
RODS = [(12, 40, 90), (8, 40, 210), (5, 40, 330)]  # radius mm, distance from the axis mm, angle deg


def phantom(xs, ys):
    img = (np.hypot(xs, ys) <= 80).astype(float)
    for r, d, a in RODS:
        cx, cy = d * np.cos(np.radians(a)), d * np.sin(np.radians(a))
        img[np.hypot(xs - cx, ys - cy) <= r] = 4.0
    return img


def main(dst):
    first = -104
    header = SimpleNamespace(r=np.arange(first, -first + 1), views=192)
    s, phi = project.bin_lines(header)
    proj = project.Projector(s, phi, n=128, pixel_mm=2.0)
    xs, ys = proj.pixel_centers()
    truth = phantom(xs, ys)
    clean = proj.forward(truth)
    trues = 684_000
    clean *= trues / clean.sum()
    add = np.full(clean.shape, 366_000 / clean.size)
    rng = np.random.default_rng(28)
    y = rng.poisson(clean + add).astype(float)
    shots = {}
    mlem.osem(y, proj, 1.0, add, max(SHOW), n_subsets=8,
              callback=lambda it, x: shots.__setitem__(it, x.copy()) if it in SHOW else None)
    bg = (np.hypot(xs, ys) <= 60)
    for r, d, a in RODS:
        cx, cy = d * np.cos(np.radians(a)), d * np.sin(np.radians(a))
        bg &= np.hypot(xs - cx, ys - cy) >= r + 12
    fig, axes = d2d.figure(height=2.55, width=1.0, nrows=2, ncols=4)
    panels = [("the phantom", truth, None), ("its sinogram, 192 views", y, None)] + \
             [(f"iteration {k}", shots[k], k) for k in SHOW]
    for ax, (title, img, k) in zip(axes.ravel(), panels):
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        if k is None and img is y:
            ax.imshow(img, cmap="gray_r", aspect="auto", interpolation="nearest")
            ax.set_xlabel("radial bin", fontsize=d2d.FONT_PT - 1.5)
            ax.set_ylabel("view", fontsize=d2d.FONT_PT - 1.5)
        else:
            ax.imshow(img[24:104, 24:104], cmap="magma", vmin=0, vmax=np.percentile(img, 99.8), interpolation="nearest")
            if k is not None:
                cov = img[bg].std() / img[bg].mean() * 100
                ax.text(0.03, 0.03, f"noise {cov:.0f}%", transform=ax.transAxes, fontsize=d2d.FONT_PT - 1.5, color="white")
        ax.set_title(title, fontsize=d2d.FONT_PT - 0.5, color=d2d.INK, pad=2)
    fig.tight_layout(pad=0.3, w_pad=0.3, h_pad=0.6)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
