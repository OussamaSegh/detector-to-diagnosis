# SPDX-License-Identifier: MIT
"""The projector of Exercise 28.3, given: the parallel-beam pair of Exercise 28.1 (an n x n image
of unit pixels, `views` angles over 180 degrees, `bins` radial bins of width 1), with back() the
exact adjoint of forward(), for all the views or a subset of them."""
import numpy as np


class Projector:
    def __init__(self, n=32, views=36, bins=41):
        self.n, self.views, self.bins = n, views, bins
        c = np.arange(n) - (n - 1) / 2.0
        self.x, self.y = np.meshgrid(c, c, indexing="xy")
        self._splats = []
        for v in range(views):
            phi = v * np.pi / views
            f = (self.x * np.cos(phi) + self.y * np.sin(phi)).ravel() + (bins - 1) / 2.0
            lo = np.floor(f).astype(np.int64)
            frac = f - lo
            pairs = []
            for b, w in ((lo, 1.0 - frac), (lo + 1, frac)):
                ok = (b >= 0) & (b < bins)
                pairs.append((np.flatnonzero(ok), b[ok], w[ok]))
            self._splats.append(pairs)

    def forward(self, image, views=None):
        """The projections of the given views (all by default), one row per view in that order."""
        vs = range(self.views) if views is None else list(views)
        flat = np.asarray(image, dtype=np.float64).ravel()
        out = np.zeros((len(vs), self.bins))
        for k, v in enumerate(vs):
            for pix, b, w in self._splats[v]:
                out[k] += np.bincount(b, flat[pix] * w, self.bins)
        return out

    def back(self, sino, views=None):
        """The adjoint for the given views: row k of sino belongs to views[k]."""
        vs = range(self.views) if views is None else list(views)
        sino = np.asarray(sino, dtype=np.float64)
        out = np.zeros(self.n * self.n)
        for k, v in enumerate(vs):
            for pix, b, w in self._splats[v]:
                out[pix] += w * sino[k, b]
        return out.reshape(self.n, self.n)
