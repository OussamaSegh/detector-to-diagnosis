# SPDX-License-Identifier: MIT
"""Timing calibration: each channel's delay, from the time differences of coincident pairs.

A pair of singles from one annihilation, seen by crystals i and j, has the time difference

    t_i - t_j = (d_i - d_j) + (TOF_ij) + noise

where d is a channel's delay and TOF_ij the difference of the two photons' flights. For a uniform
cylinder centred in the ring, the activity along each line between two crystals is symmetric about
the line's midpoint, so the mean TOF of each pair of crystals is zero, and the delays are the
least-squares solution of

    minimise  sum over pairs (t_i - t_j - d_i + d_j)^2,

up to a constant that no coincidence can see (it is fixed by asking for delays of mean zero). The
normal equations are L d = r, with L the Laplacian of the graph whose nodes are crystals and whose
edges are pairs: L_ii the number of pairs crystal i is in, L_ij minus the pairs of i with j, and
r_i the sum of (t_i - t_j) over the pairs of i. L is sparse, symmetric and positive semi-definite,
so conjugate gradients solve it with two bincounts per iteration and no matrix in memory.

The solution is only as good as the graph is connected. A point source at the centre gives each
crystal pairs with the few crystals opposite it, joined to the rest only by the pairs that
non-collinearity and depth of interaction add: the system is badly conditioned (about 740
iterations, against about 60) and the delays come out 130 ps rms wrong (Chapter 26). A cylinder
gives each crystal pairs with a fan of crystals across the ring, and the delays come out 21 ps rms
wrong.

Some pairs are random coincidences: two photons of different annihilations, whose time difference is
anything in the window. They pull every delay toward zero and widen the residual, so solve() trims
them: it solves, drops the pairs whose residual is more than four robust standard deviations from
zero, and solves again with the rest, until no more pairs are dropped.
"""
import numpy as np

from . import readout


# [snippet:pairs]
def pairs(t, crystal, energy_kev, window_ps=4_000, lo_kev=430.0, hi_kev=590.0):
    """The coincident pairs of a stream of singles: indices (i, j) of two singles in the energy
    window, closer than window_ps, with no third single of the window within window_ps of either.

    The isolated pairs only, as the sorter's kill_all policy keeps them (Chapter 10): a calibration
    needs few, clean pairs more than many doubtful ones. Assumes t is sorted."""
    sel = np.flatnonzero((energy_kev >= lo_kev) & (energy_kev <= hi_kev))
    ts = t[sel]
    if ts.size < 2:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    gap_next = np.diff(ts)                      # between k and k+1
    close = gap_next < window_ps
    before = np.concatenate(([np.inf], gap_next))[:-1]   # between k-1 and k
    after = np.concatenate((gap_next[1:], [np.inf]))      # between k+1 and k+2
    k = np.flatnonzero(close & (before >= window_ps) & (after >= window_ps))
    i, j = sel[k], sel[k + 1]
    keep = crystal[i] != crystal[j]
    return i[keep], j[keep]
# [/snippet:pairs]


# [snippet:solve]
def solve_delays(ci, cj, dt, n_crystals=readout.NUM_CRYSTALS, tol=1e-6, max_iter=2_000):
    """The delays d (mean zero, ps) that best explain dt = d[ci] - d[cj] + noise, by conjugate
    gradients on L d = r. Crystals in no pair get 0. Returns (d, rms residual in ps, iterations)."""
    deg = np.bincount(ci, minlength=n_crystals) + np.bincount(cj, minlength=n_crystals)
    deg = deg.astype(float)
    r = (np.bincount(ci, weights=dt, minlength=n_crystals)
         - np.bincount(cj, weights=dt, minlength=n_crystals))

    def lap(x):  # L x = deg * x - (sum of the neighbours' x)
        return deg * x - np.bincount(ci, weights=x[cj], minlength=n_crystals) - np.bincount(
            cj, weights=x[ci], minlength=n_crystals)

    seen = deg > 0
    r = np.where(seen, r - r[seen].mean(), 0.0)    # in the range of L: orthogonal to the constants
    d = np.zeros(n_crystals)
    res = r.copy()
    p = res.copy()
    rr = res @ res
    norm0 = np.sqrt(rr) if rr > 0 else 1.0
    it = 0
    while it < max_iter and np.sqrt(rr) > tol * norm0:
        lp = lap(p)
        alpha = rr / (p @ lp)
        d += alpha * p
        res -= alpha * lp
        rr_new = res @ res
        p = res + (rr_new / rr) * p
        rr = rr_new
        it += 1
    d = np.where(seen, d - d[seen].mean(), 0.0)
    resid = dt - (d[ci] - d[cj])
    rms = float(np.sqrt(np.mean(resid ** 2))) if dt.size else 0.0
    return d, rms, it
# [/snippet:solve]


# [snippet:trim]
def solve(ci, cj, dt, n_crystals=readout.NUM_CRYSTALS, k=4.0, rounds=8):
    """solve_delays() on the pairs that are not outliers: after each solution, the pairs whose
    residual is beyond k robust standard deviations (1.4826 times the median absolute residual)
    are set aside and the rest solved again. Returns (d, rms residual of the kept pairs in ps,
    the kept pairs as a boolean mask, total iterations)."""
    keep = np.ones(dt.size, dtype=bool)
    total = 0
    for _ in range(rounds):
        d, _, it = solve_delays(ci[keep], cj[keep], dt[keep], n_crystals)
        total += it
        resid = dt - (d[ci] - d[cj])
        sigma = 1.4826 * np.median(np.abs(resid[keep]))
        new_keep = np.abs(resid) <= k * sigma
        if np.array_equal(new_keep, keep):
            break
        keep = new_keep
    rms = float(np.sqrt(np.mean(resid[keep] ** 2))) if keep.any() else 0.0
    return d, rms, keep, total
# [/snippet:trim]
