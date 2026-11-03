# SPDX-License-Identifier: MIT
"""Projectors for Exercise 29.3, given: the parallel-beam pair of Exercise 28.1 (an n x n image of
unit pixels, `views` angles over 180 degrees, `bins` radial bins of width 1), and variants of it,
some of which are wrong."""
import numpy as np


class Parallel:
    def __init__(self, n=32, views=36, bins=41, dtype=np.float64, phi_shift=0.0, s_sign=1.0,
                 nearest_back=False, scale=1.0):
        self.n, self.views, self.bins, self.shape = n, views, bins, (views, bins)
        self.dtype, self.nearest_back, self.scale = dtype, nearest_back, scale
        c = np.arange(n) - (n - 1) / 2.0
        x, y = np.meshgrid(c, c, indexing="xy")
        self._splat = []
        for v in range(views):
            phi = v * np.pi / views + phi_shift
            f = s_sign * (x * np.cos(phi) + y * np.sin(phi)).ravel() + (bins - 1) / 2.0
            lo = np.floor(f).astype(np.int64)
            self._splat.append((lo, (f - lo).astype(dtype)))

    def forward(self, image):
        flat = np.asarray(image, dtype=self.dtype).ravel()
        out = np.zeros((self.views, self.bins), dtype=self.dtype)
        for v, (lo, frac) in enumerate(self._splat):
            for b, w in ((lo, 1 - frac), (lo + 1, frac)):
                ok = (b >= 0) & (b < self.bins)
                out[v] += np.bincount(b[ok], (flat * w)[ok], self.bins).astype(self.dtype)
        return out * self.scale

    def back(self, sino):
        sino = np.asarray(sino, dtype=self.dtype)
        out = np.zeros(self.n * self.n, dtype=self.dtype)
        for v, (lo, frac) in enumerate(self._splat):
            if self.nearest_back:
                b = np.where(frac < 0.5, lo, lo + 1)
                ok = (b >= 0) & (b < self.bins)
                out[ok] += sino[v, b[ok]]
                continue
            for b, w in ((lo, 1 - frac), (lo + 1, frac)):
                ok = (b >= 0) & (b < self.bins)
                out[ok] += w[ok] * sino[v, b[ok]]
        return out.reshape(self.n, self.n) * self.scale
