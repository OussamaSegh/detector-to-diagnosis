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


# [snippet:tof]
C_MM_PER_PS = 0.299792458


def tof_bins_mm(tof_bins, tof_bin_ps):
    """The centers along the line, in mm, of the TOF bins of MiniDAQ's histogrammer: bin k holds
    tau = t_a - t_b in [(k - K/2) w, (k + 1 - K/2) w), and an annihilation at l along the line
    (from a towards b, 0 at the line's middle) arrives with tau = 2 l / c."""
    k = np.arange(tof_bins)
    return (k - (tof_bins - 1) / 2.0) * tof_bin_ps * C_MM_PER_PS / 2.0


class TofProjector(Projector):
    """A @ x and A.T @ y with time of flight: each line is split into tof_bins bins along its
    length, and a step of the line at l contributes to bin k with the probability that its tau
    falls in that bin, for a Gaussian timing error of FWHM ctr_fwhm_ps (the coincidence time
    resolution). Arrays (views, radial, tof_bins); the sum over the TOF bins is the projection
    without TOF, less what falls outside the outer bins, which the histogrammer drops too.

    The direction along each line is (-sin phi, cos phi) for the bin's own angle phi, and endpoint
    a of the histogrammer's bins lies at negative l (Chapter 39)."""

    def __init__(self, s_mm, phi, n=128, pixel_mm=2.0, tof_bins=13, tof_bin_ps=100.0,
                 ctr_fwhm_ps=300.0):
        super().__init__(s_mm, phi, n=n, pixel_mm=pixel_mm)
        if tof_bins < 1 or tof_bin_ps <= 0 or ctr_fwhm_ps <= 0:
            raise ValueError("tof_bins, tof_bin_ps and ctr_fwhm_ps must be positive")
        self.tof_bins = int(tof_bins)
        self.shape = (*s_mm.shape, self.tof_bins)
        centers = tof_bins_mm(self.tof_bins, tof_bin_ps)
        half = tof_bin_ps * C_MM_PER_PS / 4.0
        self._edges = np.append(centers - half, centers[-1] + half)  # the bins touch: K + 1 edges
        self._sigma_mm = ctr_fwhm_ps / (2.0 * np.sqrt(2.0 * np.log(2.0))) * C_MM_PER_PS / 2.0
        self._along = [self._positions(s_mm[v], phi[v]) for v in range(s_mm.shape[0])]

    def _positions(self, s, phi):
        """l of each step of each line of a view, (lines, n): where the step's point lies along
        the line, measured from the foot of the normal (the line's middle on the scanner)."""
        n, p = self.n, self.pixel_mm
        dx, dy = -np.sin(phi), np.cos(phi)
        centers = (np.arange(n) - (n - 1) / 2.0) * p
        if np.mean(np.abs(dx)) >= np.mean(np.abs(dy)):
            return (centers[None, :] - (s * np.cos(phi))[:, None]) / dx[:, None]
        return (centers[None, :] - (s * np.sin(phi))[:, None]) / dy[:, None]

    def _kernel(self, v):
        """(lines, n, tof_bins): the probability of each TOF bin for each step of view v."""
        z = np.sqrt(2.0) * self._sigma_mm
        return 0.5 * np.diff(erf((self._edges - self._along[v][..., None]) / z), axis=-1)

    def forward(self, image, views=None):
        flat = np.asarray(image, dtype=np.float64).ravel()
        vs = range(self.shape[0]) if views is None else views
        out = np.zeros((len(vs), self.shape[1], self.tof_bins))
        for k, v in enumerate(vs):
            idx, w = self._views[v]
            per_step = (flat[idx] * w).sum(axis=2)                # (lines, n)
            out[k] = np.einsum("ls,lsk->lk", per_step, self._kernel(v))
        return out

    def back(self, sino, views=None):
        vs = range(self.shape[0]) if views is None else views
        out = np.zeros(self.n * self.n)
        for k, v in enumerate(vs):
            idx, w = self._views[v]
            per_step = np.einsum("lk,lsk->ls", np.asarray(sino[k], dtype=np.float64), self._kernel(v))
            out += np.bincount(idx.ravel(), (w * per_step[:, :, None]).ravel(), self.n * self.n)
        return out.reshape(self.n, self.n)


def erf(x):
    """The error function, elementwise: Abramowitz and Stegun 7.1.26, within 1.5e-7 of the exact
    value (numpy has no erf, and scipy is not a dependency of the tool). The projector and its
    adjoint use the same values, so the adjoint holds to rounding whatever the approximation."""
    x = np.asarray(x, dtype=np.float64)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027
                                                                          + t * 1.061405429))))
    return np.sign(x) * (1.0 - poly * np.exp(-a * a))


# [/snippet:tof]


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


class CppTofProjector(CppProjector):
    """TofProjector's interface on the C++ projector (Chapter 39)."""

    def __init__(self, s_mm, phi, n=128, pixel_mm=2.0, tof_bins=13, tof_bin_ps=100.0,
                 ctr_fwhm_ps=300.0, threads=0):
        self._p = load_cpp().TofProjector(s_mm, phi, n, pixel_mm, tof_bins, tof_bin_ps,
                                          ctr_fwhm_ps, threads)
        self.n, self.pixel_mm = n, float(pixel_mm)
        self.tof_bins = int(tof_bins)
        self.shape = (*np.shape(s_mm), self.tof_bins)
