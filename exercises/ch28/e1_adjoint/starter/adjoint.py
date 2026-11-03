# SPDX-License-Identifier: MIT
"""Exercise 28.1: a backprojector that is the exact adjoint of its projector.

Parallel-beam geometry: an n x n image of pixels of 1 (unit) centered on the axis, `views` angles
phi_v = v pi / views, and `bins` radial bins of width 1 centered on s = 0. forward() is given: each
pixel's value goes to the two radial bins nearest to s = x cos(phi) + y sin(phi), split linearly.
"""
import numpy as np


def geometry(n=32, views=36, bins=41):
    c = np.arange(n) - (n - 1) / 2.0
    x, y = np.meshgrid(c, c, indexing="xy")
    phi = np.arange(views) * np.pi / views
    return {"n": n, "views": views, "bins": bins, "x": x, "y": y, "phi": phi}


def _splat(g, v):
    """For view v: each pixel's two bins (lo, lo + 1) and their weights, as flat arrays."""
    s = g["x"] * np.cos(g["phi"][v]) + g["y"] * np.sin(g["phi"][v])
    f = s.ravel() + (g["bins"] - 1) / 2.0          # fractional bin index
    lo = np.floor(f).astype(np.int64)
    frac = f - lo
    return lo, frac


def forward(img, g):
    """The projection (views, bins): every pixel splatted linearly onto its two nearest bins."""
    out = np.zeros((g["views"], g["bins"]))
    flat = np.asarray(img, dtype=np.float64).ravel()
    for v in range(g["views"]):
        lo, frac = _splat(g, v)
        for b, w in ((lo, 1.0 - frac), (lo + 1, frac)):
            ok = (b >= 0) & (b < g["bins"])
            out[v] += np.bincount(b[ok], (flat * w)[ok], g["bins"])
    return out


def back(sino, g):
    """Backprojection: each pixel takes, in every view, the bin nearest to its s."""
    out = np.zeros(g["n"] * g["n"])
    sino = np.asarray(sino, dtype=np.float64)
    for v in range(g["views"]):
        lo, frac = _splat(g, v)
        b = np.where(frac < 0.5, lo, lo + 1)
        ok = (b >= 0) & (b < g["bins"])
        out[ok] += sino[v, b[ok]]
    return out.reshape(g["n"], g["n"])


def sensitivity(g, mult=None):
    """How much each pixel contributes to the data, the denominator of MLEM: every pixel inside
    the field of view sees every view once."""
    return np.full((g["n"], g["n"]), float(g["views"]))
