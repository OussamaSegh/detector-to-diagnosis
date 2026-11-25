# SPDX-License-Identifier: MIT
"""Figure for Chapter 27: the corrections on a brain-like slice. A synthetic head (book/figures/
lib/phantoms.py: cortex, white matter, deep gray matter, ventricles, one small lesion, a skull)
is forward-projected with the chapter's projector (tools/recon) over MiniDAQ's 192 views. The
measured sinogram gets the attenuation of the head, a smooth scatter term of 25% of the trues
(the trues blurred by 60 mm along each view, as single scatter roughly is), uniform randoms of 10%,
and Poisson noise at about 3 M trues, seed 27. Then OSEM (8 subsets, 6 iterations) three times:
with every correction in the model, without attenuation correction (scaled to the same mean over the
brain), without scatter correction.

    python3 book/tools/figures.py build book/figures/plots/ch27/brain.py screen 6 pdf "tools/recon/project.py tools/recon/mlem.py"
"""
import pathlib
import sys
from types import SimpleNamespace

import numpy as np

import d2d
import phantoms

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.recon import mlem, project  # noqa: E402

TRUES = 3_000_000
SCATTER_FRACTION = 0.25
RANDOMS_FRACTION = 0.10


def blur_views(sino, s_mm, sigma_mm):
    """Each view convolved with a Gaussian of sigma_mm along the radial direction."""
    step = float(np.median(np.abs(np.diff(s_mm[0]))))
    r = int(np.ceil(3 * sigma_mm / step))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) * step / sigma_mm) ** 2)
    k /= k.sum()
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="full")[r:r + len(v)], 1, sino)


def main(dst):
    first = -104
    header = SimpleNamespace(r=np.arange(first, -first + 1), views=192)
    s, phi = project.bin_lines(header)
    proj = project.Projector(s, phi, n=128, pixel_mm=2.0)
    xs, ys = proj.pixel_centers()
    act, mu = phantoms.brain(xs, ys)
    att = np.exp(-proj.forward(mu))           # survival probability of each line
    trues = att * proj.forward(act)
    scale = TRUES / trues.sum()
    trues *= scale
    scatter = blur_views(trues, s, 60.0)
    scatter *= SCATTER_FRACTION * trues.sum() / scatter.sum()
    randoms = np.full(trues.shape, RANDOMS_FRACTION * trues.sum() / trues.size)
    rng = np.random.default_rng(27)
    y = rng.poisson(trues + scatter + randoms).astype(float)

    def recon(mult, add):
        return mlem.osem(y, proj, mult, add, 6, n_subsets=8) / scale

    full = recon(att, scatter + randoms)
    no_ac = recon(np.ones_like(att), scatter + randoms)
    no_sc = recon(att, randoms)
    # Without attenuation correction the image's scale is meaningless (every line is too low); show
    # it at the same mean over the brain, so that its shape, not its level, is compared.
    inside = act > 0.5
    no_ac *= full[inside].mean() / no_ac[inside].mean()

    fig, axes = d2d.figure(height=4.3, width=1.0, nrows=2, ncols=4)
    crop = (slice(14, 114), slice(20, 108))
    top = [("attenuation map $\\mu$ (1/mm)", mu, d2d.CMAP, (0, 0.018), None),
           ("attenuation factors $e^{\\int\\mu}$", 1 / att, d2d.CMAP, (1, None), "sino"),
           ("the measured sinogram", y, d2d.CMAP, (0, None), "sino"),
           ("the object (uptake)", act, d2d.CMAP, (0, 8.5), None)]
    vmax = np.percentile(full, 99.7)
    bottom = [("every correction", full), ("no attenuation correction", no_ac),
              ("no scatter correction", no_sc)]
    for ax, (title, img, cmap, (lo, hi), kind) in zip(axes[0], top):
        if kind == "sino":
            ax.imshow(img, cmap=cmap, vmin=lo, vmax=hi, aspect="auto", interpolation="nearest")
        else:
            ax.imshow(img[crop], cmap=cmap, vmin=lo, vmax=hi, interpolation="nearest", origin="lower")
        ax.set_title(title, fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, pad=2)
    for ax, (title, img) in zip(axes[1], bottom):
        ax.imshow(img[crop], cmap=d2d.CMAP, vmin=0, vmax=vmax, interpolation="nearest", origin="lower")
        ax.set_title(f"OSEM: {title}", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, pad=2)
    prof_y = 64 + 40 // 2  # the row through the lesion (y = 40 mm at 2 mm pixels)
    ax = axes[1][3]
    x_mm = xs[0]
    for img, lab, k in ((act, "object", 0), (full, "every correction", 1), (no_ac, "no attenuation corr.", 2),
                        (no_sc, "no scatter corr.", 3)):
        ax.plot(x_mm, img[prof_y], color=d2d.MUTED if k == 0 else d2d.CAT[k - 1], ls=d2d.DASHES[k],
                lw=d2d.LINE_PT, label=lab)
    ax.set_xlim(-80, 80)
    ax.set_xlabel("x, mm (row through the lesion)", fontsize=d2d.FONT_PT - 1.5)
    ax.legend(fontsize=d2d.FONT_PT - 2.2, frameon=False, loc="upper left")
    ax.set_title("a profile", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK, pad=2)
    for row in axes:
        for a in row:
            if a is not ax:
                a.set_xticks([])
                a.set_yticks([])
                for sp in a.spines.values():
                    sp.set_visible(False)
    fig.tight_layout(pad=0.3, w_pad=0.4, h_pad=0.8)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
