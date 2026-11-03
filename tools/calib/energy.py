# SPDX-License-Identifier: MIT
"""Energy calibration: each crystal's photopeak, and the curve that puts it at 511 keV.

The board reports an energy code c for each single. For an uncalibrated crystal, the code of a
photon that deposited E is c = g * S(E) / 0.5 keV, where g is the crystal's gain and S the SiPM's
response: S(E) = E_sat (1 - exp(-E / E_sat)), which saturates as more of the SiPM's cells fire.
E_sat is a property of the sensor type, measured once on the bench; g is what this procedure finds,
crystal by crystal, from the position of the 511 keV photopeak in the crystal's code spectrum.

The server applies a quadratic, E = a + b c + q c^2 (minidaq/processing/calibration.hpp), so the
inverse E = -E_sat ln(1 - 0.5 c / (g E_sat)) is fitted with one, by least squares over the codes
that photons of 200 to 700 keV give: the energy window and the scatter just below it. Down to 100
keV, a quadratic would be 1.5% off somewhere for an E_sat of 1500 keV; from 200 keV it is within
0.5%. fit_curve() returns how far the quadratic is from the exact inverse over the range, which the
acceptance criteria bound.
"""
import numpy as np

from . import readout

PEAK_KEV = 511.0


def saturate(e_kev, e_sat):
    """The SiPM's response to a deposited energy (identity for e_sat == 0)."""
    e = np.asarray(e_kev, dtype=float)
    return e if e_sat == 0 else e_sat * -np.expm1(-e / e_sat)


def desaturate(s_kev, e_sat):
    """The deposited energy that gives a response s (identity for e_sat == 0)."""
    s = np.asarray(s_kev, dtype=float)
    return s if e_sat == 0 else -e_sat * np.log1p(-s / e_sat)


WIDTH = 4  # codes per bin: 2 keV, a twenty-fifth of the photopeak's FWHM


def spectra(crystal, code, n_crystals=readout.NUM_CRYSTALS, width=WIDTH):
    """One histogram of codes per crystal, `width` codes per bin: shape (n_crystals, 2048/width).
    Bin k holds the codes k*width to (k+1)*width - 1."""
    bins = (readout.MAX_CODE + 1) // width
    flat = np.bincount(crystal * bins + code // width, minlength=n_crystals * bins)
    return flat.reshape(n_crystals, bins).astype(np.int32)


def photopeaks(h, width=WIDTH, chunk=2048):
    """fit_photopeaks() on spectra of `width` codes per bin, in chunks of crystals, with the
    centre and sigma in codes."""
    out = [fit_photopeaks(h[i:i + chunk], lo=300 // width, hi=2000 // width,
                          smooth=max(3, 36 // width))
           for i in range(0, h.shape[0], chunk)]
    centre, sigma, counts, ok = (np.concatenate(v) for v in zip(*out))
    return centre * width + (width - 1) / 2.0, sigma * width, counts, ok


# [snippet:peak]
def fit_photopeaks(h, lo, hi, smooth):
    """The photopeak of each spectrum (rows of h): centre and sigma in bins, and counts.

    1. The peak's first guess is the highest bin of the spectrum smoothed over `smooth` bins,
       between bins lo and hi: above most of the Compton continuum and below saturation.
    2. A window of +-2 sigma around it (sigma guessed as 6% of the centre, a typical LYSO
       resolution) is fitted as a Gaussian on a straight background: the background is the line
       through the mean counts just outside the window, and the Gaussian is found by Guo's
       weighted fit of a parabola to the logarithm of what is left (IEEE Signal Process. Mag.
       28(5), 2011), which needs no starting values and no iteration.
    3. Steps 2 and 3 are repeated twice with the window from the new sigma.

    All crystals at once, with array operations. Returns (centre, sigma, counts, ok); ok is False
    where the fit had too few points or gave a parabola that opens upward.
    """
    n, bins = h.shape
    kernel = np.ones(smooth) / smooth
    sm = np.apply_along_axis(lambda r: np.convolve(r, kernel, mode="same"), 1, h.astype(float))
    centre = lo + np.argmax(sm[:, lo:hi], axis=1).astype(float)
    sigma = 0.06 * centre
    x = np.arange(bins, dtype=float)
    ok = np.ones(n, dtype=bool)
    counts = np.zeros(n)
    for _ in range(3):
        w_lo = np.clip(np.round(centre - 2 * sigma), 1, bins - 2).astype(int)
        w_hi = np.clip(np.round(centre + 2 * sigma), 1, bins - 2).astype(int)
        side = np.maximum(2, ((w_hi - w_lo) // 8)).astype(int)
        cols = np.arange(bins)[None, :]
        inside = (cols >= w_lo[:, None]) & (cols <= w_hi[:, None])
        left = (cols >= (w_lo - side)[:, None]) & (cols < w_lo[:, None])
        right = (cols > w_hi[:, None]) & (cols <= (w_hi + side)[:, None])
        bl = (h * left).sum(1) / np.maximum(left.sum(1), 1)
        br = (h * right).sum(1) / np.maximum(right.sum(1), 1)
        xl = (w_lo - (side + 1) / 2.0)
        xr = (w_hi + (side + 1) / 2.0)
        slope = (br - bl) / np.maximum(xr - xl, 1.0)
        background = bl[:, None] + slope[:, None] * (x[None, :] - xl[:, None])
        y = np.where(inside, h - background, 0.0)
        y = np.where(y > 0, y, 0.0)
        # Guo: minimise sum y^2 (ln y - (A + B u + C u^2))^2, u centred for conditioning.
        u = (x[None, :] - centre[:, None])
        w = y * y
        ly = np.log(np.where(y > 0, y, 1.0))
        s = [(w * u ** k).sum(1) for k in range(5)]
        t = [(w * ly * u ** k).sum(1) for k in range(3)]
        m = np.stack([np.stack([s[0], s[1], s[2]], -1), np.stack([s[1], s[2], s[3]], -1),
                      np.stack([s[2], s[3], s[4]], -1)], -2)
        rhs = np.stack(t, -1)
        good = (np.abs(np.linalg.det(m)) > 1e-12) & ((y > 0).sum(1) >= 5)
        m[~good] = np.eye(3)
        rhs[~good] = 0.0
        abc = np.linalg.solve(m, rhs[..., None])[..., 0]
        b, c = abc[:, 1], abc[:, 2]
        good &= c < 0
        c = np.where(good, c, -1.0)
        new_centre = centre - b / (2 * c)
        new_sigma = np.sqrt(-1.0 / (2 * c))
        good &= np.isfinite(new_centre) & np.isfinite(new_sigma) & (new_sigma > 0.5)
        good &= (new_centre > w_lo - 1) & (new_centre < w_hi + 1)
        centre = np.where(good, new_centre, centre)
        sigma = np.where(good, new_sigma, sigma)
        ok &= good
        counts = y.sum(1)
    return centre, sigma, counts, ok
# [/snippet:peak]


# [snippet:curve]
def fit_curve(gain, e_sat, e_lo=200.0, e_hi=700.0, points=64):
    """The quadratic a + b c + q c^2 nearest to the exact inverse of c = g S(E) / 0.5, for each
    gain g, over the codes of energies e_lo to e_hi. Returns (a, b, q, worst relative error)."""
    g = np.atleast_1d(np.asarray(gain, dtype=float))
    e = np.linspace(e_lo, e_hi, points)
    c = g[:, None] * saturate(e, e_sat)[None, :] / readout.ENERGY_LSB_KEV  # codes, per crystal
    # Least squares per crystal on [1, c, c^2], scaled for conditioning.
    scale = c.max(1, keepdims=True)
    v = c / scale
    basis = np.stack([np.ones_like(v), v, v * v], -1)
    # Normal equations, batched (numpy 1.26 has no batched lstsq); the scaling keeps them tame.
    ata = np.einsum("nki,nkj->nij", basis, basis)
    atb = np.einsum("nki,nk->ni", basis, np.broadcast_to(e, c.shape))
    coef = np.linalg.solve(ata, atb[..., None])[..., 0]
    a = coef[:, 0]
    b = coef[:, 1] / scale[:, 0]
    q = coef[:, 2] / scale[:, 0] ** 2
    fit = a[:, None] + b[:, None] * c + q[:, None] * c * c
    worst = np.max(np.abs(fit - e[None, :]) / e[None, :], axis=1)
    return a, b, q, worst
# [/snippet:curve]


def gains_from_peaks(centre_code, e_sat):
    """The gain that puts a photopeak at code `centre_code` at 511 keV."""
    return np.asarray(centre_code, dtype=float) * readout.ENERGY_LSB_KEV / saturate(PEAK_KEV, e_sat)


def apply(code, crystal, a, b, q):
    """Calibrated energies in keV of codes measured by these crystals."""
    c = np.asarray(code, dtype=float)
    return a[crystal] + c * (b[crystal] + c * q[crystal])
