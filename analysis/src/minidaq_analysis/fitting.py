# SPDX-License-Identifier: MIT
"""Fits of histograms with uncertainties: a photopeak, a timing peak, any model of counts per bin.

Two estimators, because the difference matters at low counts:

- ``neyman``: least squares weighted by the observed counts, sigma_i = sqrt(max(n_i, 1)), which is
  what ``scipy.optimize.curve_fit`` does when it is handed the square root of the counts. It is
  biased: a bin that fluctuated low gets a small sigma and pulls the curve down, so a peak's area
  comes out low by about one count per bin (Exercise 31.2 and measurements/ch31 measure it).
- ``poisson``: maximum likelihood for Poisson counts, which minimizes the deviance
  2 sum(mu - n + n ln(n / mu)) (Cash's statistic). It is unbiased to first order at any count.

Every model gives the expected counts of a bin from the bin's edges, integrated over the bin, so a
peak only a few bins wide is fitted correctly. A result carries the covariance matrix, and derived
quantities (an energy resolution, a FWHM) propagate it, correlations included.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt
from scipy import optimize, special, stats

FloatArray = npt.NDArray[np.float64]
SIGMA_TO_FWHM = 2.0 * math.sqrt(2.0 * math.log(2.0))  # 2.3548...
Method = Literal["poisson", "neyman"]


@dataclass(frozen=True)
class Histogram:
    counts: FloatArray
    edges: FloatArray

    def __post_init__(self) -> None:
        if self.edges.ndim != 1 or self.counts.shape != (self.edges.size - 1,):
            raise ValueError("a histogram needs one more edge than bins")
        if np.any(np.diff(self.edges) <= 0):
            raise ValueError("histogram edges must increase")

    @staticmethod
    def of(values: npt.ArrayLike, edges: npt.ArrayLike) -> Histogram:
        e = np.asarray(edges, dtype=np.float64)
        counts, _ = np.histogram(np.asarray(values, dtype=np.float64), bins=e)
        return Histogram(counts.astype(np.float64), e)

    @property
    def centers(self) -> FloatArray:
        return 0.5 * (self.edges[1:] + self.edges[:-1])

    def __add__(self, other: Histogram) -> Histogram:
        if not np.array_equal(self.edges, other.edges):
            raise ValueError("histograms with different edges")
        return Histogram(self.counts + other.counts, self.edges)

    def window(self, lo: float, hi: float) -> Histogram:
        """The bins that lie entirely within [lo, hi]."""
        keep = (self.edges[:-1] >= lo) & (self.edges[1:] <= hi)
        idx = np.flatnonzero(keep)
        if idx.size < 1:
            raise ValueError(f"no bin within [{lo}, {hi}]")
        return Histogram(self.counts[idx], self.edges[idx[0]:idx[-1] + 2])


# A model: expected counts of each bin [lo, hi), for a parameter vector.
Model = Callable[[FloatArray, FloatArray, FloatArray], FloatArray]


# [snippet:models]
def gaussian_counts(lo: FloatArray, hi: FloatArray, area: float, mean: float,
                    sigma: float) -> FloatArray:
    """Counts of a Gaussian of total `area` in each bin, integrated exactly over the bin."""
    s = sigma * math.sqrt(2.0)
    return np.asarray(0.5 * area * (special.erf((hi - mean) / s) - special.erf((lo - mean) / s)),
                      dtype=np.float64)


def gaussian_plus_line(x_low: float, x_high: float) -> Model:
    """area, mean, sigma, b_low, b_high: a Gaussian on a straight background whose density is
    b_low counts per unit of x at x_low and b_high at x_high. Bounding both at zero keeps the
    background physical over the whole range, which b0 + b1 x cannot do with simple bounds."""
    span = x_high - x_low

    def model(lo: FloatArray, hi: FloatArray, p: FloatArray) -> FloatArray:
        slope = (p[4] - p[3]) / span
        line = p[3] * (hi - lo) + 0.5 * slope * ((hi - x_low) ** 2 - (lo - x_low) ** 2)
        return np.asarray(gaussian_counts(lo, hi, p[0], p[1], p[2]) + line, dtype=np.float64)
    return model


def gaussian_plus_constant(lo: FloatArray, hi: FloatArray, p: FloatArray) -> FloatArray:
    """area, mean, sigma, c: a Gaussian on a flat background of c counts per unit of x."""
    return np.asarray(gaussian_counts(lo, hi, p[0], p[1], p[2]) + p[3] * (hi - lo),
                      dtype=np.float64)
# [/snippet:models]


@dataclass(frozen=True)
class FitResult:
    names: tuple[str, ...]
    values: FloatArray
    covariance: FloatArray
    statistic: float  # chi-square (neyman) or deviance (poisson) at the minimum
    ndf: int
    method: Method
    expected: FloatArray = field(repr=False)  # the model's counts per bin at the minimum
    hist: Histogram = field(repr=False)  # the bins that were fitted

    @property
    def errors(self) -> FloatArray:
        return np.sqrt(np.diag(self.covariance))

    @property
    def p_value(self) -> float:
        """Probability of a statistic at least this large if the model is right (asymptotic:
        trust it only when most bins expect five counts or more)."""
        return float(stats.chi2.sf(self.statistic, self.ndf)) if self.ndf > 0 else float("nan")

    def __getitem__(self, name: str) -> tuple[float, float]:
        i = self.names.index(name)
        return float(self.values[i]), float(self.errors[i])

    def derived(self, f: Callable[[FloatArray], float]) -> tuple[float, float]:
        """f(parameters) and its standard error, by linear propagation of the covariance with a
        numerical gradient."""
        g = _gradient(f, self.values)
        return f(self.values), float(math.sqrt(max(float(g @ self.covariance @ g), 0.0)))


def _step(v: float) -> float:
    """Step of a central difference: relative for a large parameter, and at least 1e-5 of a unit
    for one near zero. The first version took 1e-6 of max(|v|, 1e-3): for a timing peak's mean of
    0.016 ps that is 1.6e-8 ps, where the difference of two model values is mostly rounding, and
    the fit's score was noise near the minimum (CR-0017)."""
    return 1e-5 * max(abs(v), 1.0)


def _gradient(f: Callable[[FloatArray], float], p: FloatArray) -> FloatArray:
    g = np.empty_like(p)
    for i in range(p.size):
        h = _step(float(p[i]))
        up, down = p.copy(), p.copy()
        up[i] += h
        down[i] -= h
        g[i] = (f(up) - f(down)) / (2 * h)
    return g


def _jacobian(model: Model, lo: FloatArray, hi: FloatArray, p: FloatArray) -> FloatArray:
    """d expected / d parameter, one column per parameter, by central differences."""
    jac = np.empty((lo.size, p.size))
    for i in range(p.size):
        h = _step(float(p[i]))
        up, down = p.copy(), p.copy()
        up[i] += h
        down[i] -= h
        jac[:, i] = (model(lo, hi, up) - model(lo, hi, down)) / (2 * h)
    return jac


def deviance(n: FloatArray, mu: FloatArray) -> float:
    """Poisson deviance 2 sum(mu - n + n ln(n / mu)), with n ln(n / mu) = 0 where n = 0."""
    mu = np.maximum(mu, 1e-300)
    log_term = np.where(n > 0, n * np.log(np.where(n > 0, n, 1.0) / mu), 0.0)
    return float(2.0 * np.sum(mu - n + log_term))


# [snippet:fit]
def fit(hist: Histogram, model: Model, p0: Sequence[float] | FloatArray, names: Sequence[str],
        method: Method = "poisson",
        bounds: Sequence[tuple[float | None, float | None]] | None = None) -> FitResult:
    """Fits `model` to `hist`. Raises RuntimeError when the fit does not converge or its
    covariance cannot be computed, so that a failed fit can never reach a report as a number."""
    lo, hi, n = hist.edges[:-1], hist.edges[1:], hist.counts
    p_start = np.asarray(p0, dtype=np.float64)
    if len(names) != p_start.size:
        raise ValueError("one name per parameter")
    ndf = n.size - p_start.size
    if ndf < 1:
        raise ValueError(f"{n.size} bins for {p_start.size} parameters")
    if method == "neyman":
        sigma = np.sqrt(np.maximum(n, 1.0))
        lower = [-np.inf if b[0] is None else b[0] for b in bounds] if bounds else -np.inf
        upper = [np.inf if b[1] is None else b[1] for b in bounds] if bounds else np.inf
        try:
            p, cov = optimize.curve_fit(lambda _x, *q: model(lo, hi, np.asarray(q)), lo, n,
                                        p0=p_start, sigma=sigma, absolute_sigma=True,
                                        bounds=(lower, upper))
        except (RuntimeError, ValueError) as e:
            raise RuntimeError(f"fit did not converge: {e}") from None
        mu = model(lo, hi, p)
        statistic = float(np.sum(((n - mu) / sigma) ** 2))
    elif method == "poisson":
        # Start from the least-squares solution when it exists: maximum likelihood needs a start
        # near the minimum, and a background guessed from the tails of a peak is not one (the
        # first version stalled at 8 times the right deviance from such a start).
        # A least-squares solution can lie where the model expects no counts in a bin (a negative
        # background); maximum likelihood cannot start there, so the given start is the fallback.
        starts = [p_start]
        try:
            starts.insert(0, fit(hist, model, p_start, names, "neyman", bounds).values)
        except RuntimeError:
            pass
        valid = [q for q in starts if _inside(q, bounds) and np.all(model(lo, hi, q) > 0)]
        if not valid:
            raise RuntimeError("fit start gives a bin no expected counts")
        p = _fisher_scoring(model, lo, hi, n, valid[0], bounds)
        mu = model(lo, hi, p)
        # The inverse of the Fisher information, J^T diag(1/mu) J: the covariance of a maximum
        # likelihood estimate of Poisson counts.
        jac = _jacobian(model, lo, hi, p)
        try:
            cov = np.linalg.inv(jac.T @ (jac / mu[:, None]))
        except np.linalg.LinAlgError:
            raise RuntimeError("fit covariance is singular") from None
        statistic = deviance(n, mu)
    else:
        raise ValueError(f"unknown method {method!r}")
    if not np.all(np.isfinite(cov)) or np.any(np.diag(cov) < 0):
        raise RuntimeError("fit covariance is not finite")
    # A parameter whose error is wider than everything its bounds allow is not determined by the
    # data: the mean and width of a peak whose area went to zero, for instance.
    for name, err, b in zip(names, np.sqrt(np.diag(cov)), bounds or [], strict=False):
        if b[0] is not None and b[1] is not None and err > b[1] - b[0]:
            raise RuntimeError(f"fit does not determine {name}: its error {err:.3g} is wider "
                               f"than its bounds")
    return FitResult(tuple(names), np.asarray(p, dtype=np.float64), np.asarray(cov), statistic,
                     ndf, method, mu, hist)
# [/snippet:fit]


def _inside(p: FloatArray, bounds: Sequence[tuple[float | None, float | None]] | None) -> bool:
    if not bounds:
        return True
    return all((b[0] is None or v >= b[0]) and (b[1] is None or v <= b[1])
               for v, b in zip(p, bounds, strict=True))


# [snippet:scoring]
def _fisher_scoring(model: Model, lo: FloatArray, hi: FloatArray, n: FloatArray, p: FloatArray,
                    bounds: Sequence[tuple[float | None, float | None]] | None,
                    max_steps: int = 100) -> FloatArray:
    """Maximum likelihood for Poisson counts by Fisher scoring: Newton's method with the expected
    curvature J^T diag(1/mu) J instead of the exact one, the step halved until the deviance falls,
    the parameters projected onto their bounds. Converged when the fall of the deviance that a full
    step predicts, U.step with U the score J^T (n/mu - 1), is below 5e-10, or below 5e-5 when no
    step lowers the deviance any more: then the minimum is found to the precision of the
    derivatives and of the deviance's own sum, and moving on would change no parameter by a
    visible part of its error."""
    k = p.size
    box = list(bounds) if bounds else [(None, None)] * k
    low = np.array([-np.inf if b[0] is None else b[0] for b in box])
    high = np.array([np.inf if b[1] is None else b[1] for b in box])
    mu = model(lo, hi, p)
    if np.any(mu <= 0):
        raise RuntimeError("fit start gives a bin no expected counts")
    d = deviance(n, mu)
    for _ in range(max_steps):
        jac = _jacobian(model, lo, hi, p)
        score = jac.T @ (n / mu - 1.0)
        info = jac.T @ (jac / mu[:, None])
        # A parameter on a bound whose score pushes it further out stays there (projected
        # Newton): a background of zero at one end of the range is a valid maximum.
        free = ~(((p <= low) & (score < 0)) | ((p >= high) & (score > 0)))
        step = np.zeros(k)
        try:
            step[free] = np.linalg.solve(info[np.ix_(free, free)], score[free])
        except np.linalg.LinAlgError:
            raise RuntimeError("fit curvature is singular") from None
        # The deviance is -2 log L + constant: its gradient is -2 U and its expected curvature
        # 2 info, so a full step predicts a fall of 2 U.step - step.info.step = U.step.
        decrement = float(score @ step)
        if decrement < 5e-10:
            return p
        t = 1.0
        while t > 1e-10:
            q = np.clip(p + t * step, low, high)
            mu_q = model(lo, hi, q)
            if np.all(mu_q > 0) and (d_q := deviance(n, mu_q)) <= d:
                p, mu, d = q, mu_q, d_q
                break
            t *= 0.5
        else:
            # No step lowers the deviance: either the minimum is found to the precision of the
            # deviance's own sum (a predicted fall far below one unit, which moves no parameter by
            # a visible part of its error), or the fit is stuck, which is an error.
            if decrement < 5e-5:
                return p
            raise RuntimeError("fit cannot lower the deviance from where it stopped")
    raise RuntimeError(f"fit did not converge in {max_steps} steps")
# [/snippet:scoring]


def fwhm_fraction(r: FitResult) -> tuple[float, float]:
    """Energy resolution FWHM / mean of a fit with `mean` and `sigma`, and its standard error."""
    i, j = r.names.index("mean"), r.names.index("sigma")
    return r.derived(lambda p: SIGMA_TO_FWHM * abs(p[j]) / p[i])


def fwhm(r: FitResult) -> tuple[float, float]:
    """FWHM of a fit with `sigma`, and its standard error."""
    j = r.names.index("sigma")
    return r.derived(lambda p: SIGMA_TO_FWHM * abs(p[j]))


# [snippet:photopeak]
def fit_photopeak(hist: Histogram, lo: float, hi: float,
                  method: Method = "poisson") -> FitResult:
    """A Gaussian on a straight background, fitted to the bins within [lo, hi] keV."""
    h = hist.window(lo, hi)
    c, n = h.centers, h.counts
    if n.sum() < 50:
        raise ValueError(f"{n.sum():.0f} counts in [{lo}, {hi}] keV: too few for a fit")
    mean0 = float(c[np.argmax(n)])
    sigma0 = math.sqrt(max(float(np.average((c - mean0) ** 2, weights=n + 1e-9)), 1e-6))
    x0, x1 = float(h.edges[0]), float(h.edges[-1])
    width = float(np.mean(np.diff(h.edges)))
    p0 = [float(n.sum()), mean0, sigma0, 0.1 * float(n[:3].mean()) / width,
          0.1 * float(n[-3:].mean()) / width]
    bounds = [(0.0, None), (x0, x1), (1e-3 * (x1 - x0), x1 - x0), (0.0, None), (0.0, None)]
    return fit(h, gaussian_plus_line(x0, x1), p0, ("area", "mean", "sigma", "b_low", "b_high"),
               method, bounds)
# [/snippet:photopeak]


def fit_timing(hist: Histogram, method: Method = "poisson") -> FitResult:
    """A Gaussian on a flat background (the randoms are flat in time difference)."""
    c, n = hist.centers, hist.counts
    if n.sum() < 50:
        raise ValueError(f"{n.sum():.0f} counts: too few for a fit")
    mean0 = float(c[np.argmax(n)])
    width = float(np.mean(np.diff(hist.edges)))
    floor = float(np.median(np.concatenate([n[: n.size // 8 + 1], n[-(n.size // 8 + 1):]])))
    above = np.clip(n - floor, 0, None)
    sigma0 = math.sqrt(max(float(np.average((c - mean0) ** 2, weights=above + 1e-9)), width**2))
    p0 = [float(above.sum()) + 1.0, mean0, sigma0, max(floor, 0.5) / width]
    span = float(hist.edges[-1] - hist.edges[0])
    bounds = [(0.0, None), (float(hist.edges[0]), float(hist.edges[-1])), (width / 10, span),
              (0.0, None)]
    return fit(hist, gaussian_plus_constant, p0, ("area", "mean", "sigma", "background"), method,
               bounds)
