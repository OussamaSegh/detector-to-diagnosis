# SPDX-License-Identifier: MIT
"""A 2D system model for MiniDAQ's sinograms (Chapter 28): Joseph's line-integral projector and its
exact adjoint, numpy only.

A sinogram bin (view v, radial bin r) is the line of points p with p . (cos phi, sin phi) = s. For
MiniDAQ's crystals at angles (i + 1/2) 2 pi / N, the pair (i, j) with k = i + j + 1 and d = j - i
has its normal at phi = k pi / N and s = R cos(d pi / N) = -R sin(pi r / N), r = d - N / 2
(sinogram.py). Each view interleaves two angles: k = 2v where r is odd and k = 2v + 1 where it is
even. The header's phi is their mean; the projector uses each bin's own.

The image is n x n square pixels of pixel_mm, centered on the axis, indexed [row, column] = [y, x].

Two projectors have this interface: Projector, in numpy, the reference, and CppProjector, the
same algorithm in C++ (Chapter 29, module recon_cpp), which the reconstruction uses when it is
built. tools/test_recon_cpp.py runs the tests of the first on the second.
"""
import os
import sys

import numpy as np

from . import sinogram as sg


# [snippet:lines]
def bin_lines(header, radius_mm=sg.RADIUS_MM):
    """(s_mm, phi) of every (view, radial bin), arrays of shape (views, radial_bins). radius_mm is
    the radius at which the lines meet the crystals: the front faces (150 mm), or deeper, where the
    photons interact on average (measurements/ch28 finds it from a point source)."""
    r = header.r
    s = -radius_mm * np.sin(np.pi * r / sg.CRYSTALS_PER_RING)
    k = 2 * np.arange(header.views)[:, None] + (r[None, :] % 2 == 0)
    phi = k * np.pi / sg.CRYSTALS_PER_RING
    return np.broadcast_to(s, phi.shape).copy(), phi
# [/snippet:lines]


class Projector:
    """A @ x and A.T @ y for the lines (s_mm, phi) of shape (views, radial) and an n x n image.

    Joseph's method: a line steps through the image one column (or one row, for a line closer to
    the x axis) at a time, takes the image linearly interpolated between the two nearest pixels at
    each step, and weights it by the length of the step. The weights are computed once per view;
    back() scatters with exactly the same weights, so it is the adjoint of forward() to rounding,
    which the tests check with <A x, y> = <x, A^T y>."""

    def __init__(self, s_mm, phi, n=128, pixel_mm=2.0):
        self.n, self.pixel_mm = n, float(pixel_mm)
        self.shape = s_mm.shape
        self._views = [self._weights(s_mm[v], phi[v]) for v in range(s_mm.shape[0])]

    # [snippet:joseph]
    def _weights(self, s, phi):
        """(indices, weights), each (lines, n, 2): the pixels and weights of each line of a view."""
        n, p = self.n, self.pixel_mm
        nx, ny = np.cos(phi), np.sin(phi)          # the normal
        dx, dy = -ny, nx                            # the direction along the line
        centers = (np.arange(n) - (n - 1) / 2.0) * p
        along_x = np.mean(np.abs(dx)) >= np.mean(np.abs(dy))
        if along_x:   # one step per column: x = centers, y from the line
            t = (centers[None, :] - (s * nx)[:, None]) / dx[:, None]
            other = (s * ny)[:, None] + t * dy[:, None]
            step = p / np.abs(dx)
        else:         # one step per row
            t = (centers[None, :] - (s * ny)[:, None]) / dy[:, None]
            other = (s * nx)[:, None] + t * dx[:, None]
            step = p / np.abs(dy)
        f = other / p + (n - 1) / 2.0                # fractional pixel coordinate
        lo = np.floor(f).astype(np.int64)
        frac = f - lo
        w = np.stack([1.0 - frac, frac], axis=-1) * step[:, None, None]
        o = np.stack([lo, lo + 1], axis=-1)
        w = np.where((o >= 0) & (o < n), w, 0.0)     # outside the image: no weight
        o = np.clip(o, 0, n - 1)
        steps = np.broadcast_to(np.arange(n)[None, :, None], o.shape)
        idx = o * n + steps if along_x else steps * n + o   # [row, column] flattened
        return idx.astype(np.int32), w.astype(np.float32)
    # [/snippet:joseph]

    def forward(self, image, views=None):
        """The line integrals (mm times image units) of every line, or of the given views only."""
        flat = np.asarray(image, dtype=np.float64).ravel()
        vs = range(self.shape[0]) if views is None else views
        out = np.zeros((len(vs), self.shape[1]))
        for k, v in enumerate(vs):
            idx, w = self._views[v]
            out[k] = (flat[idx] * w).sum(axis=(1, 2))
        return out

    def back(self, sino, views=None):
        """The adjoint: each line's value spread over its pixels with its weights."""
        vs = range(self.shape[0]) if views is None else views
        out = np.zeros(self.n * self.n)
        for k, v in enumerate(vs):
            idx, w = self._views[v]
            out += np.bincount(idx.ravel(), (w * np.asarray(sino[k])[:, None, None]).ravel(),
                               self.n * self.n)
        return out.reshape(self.n, self.n)

    def pixel_centers(self):
        """(x, y) of every pixel center, each n x n, in mm."""
        c = (np.arange(self.n) - (self.n - 1) / 2.0) * self.pixel_mm
        return np.meshgrid(c, c, indexing="xy")


def _pixel_centers(n, pixel_mm):
    c = (np.arange(n) - (n - 1) / 2.0) * pixel_mm
    return np.meshgrid(c, c, indexing="xy")


# [snippet:cpp]
def load_cpp():
    """The module recon_cpp: from the directory in MINIDAQ_RECON_CPP if it is set (the build
    directory, as CTest sets it), else from sys.path. ImportError if it is not built."""
    where = os.environ.get("MINIDAQ_RECON_CPP")
    if where and where not in sys.path:
        sys.path.insert(0, where)
    import recon_cpp  # noqa: PLC0415 (only when asked for)
    return recon_cpp


class CppProjector:
    """Projector's interface on the C++ projector. threads = 0 uses every core."""

    def __init__(self, s_mm, phi, n=128, pixel_mm=2.0, threads=0):
        self._p = load_cpp().Projector(s_mm, phi, n, pixel_mm, threads)
        self.n, self.pixel_mm = n, float(pixel_mm)
        self.shape = tuple(np.shape(s_mm))

    def forward(self, image, views=None):
        return self._p.forward(image, None if views is None else [int(v) for v in views])

    def back(self, sino, views=None):
        return self._p.back(sino, None if views is None else [int(v) for v in views])

    def pixel_centers(self):
        return _pixel_centers(self.n, self.pixel_mm)
# [/snippet:cpp]
