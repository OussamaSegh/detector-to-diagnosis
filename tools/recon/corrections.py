# SPDX-License-Identifier: MIT
"""The corrections that turn MiniDAQ's counts into numbers proportional to activity (Chapter 27).

For a sinogram bin, the prompts P are trues T plus scatter S plus randoms R, each detected with the
bin's efficiency and the live time, and the trues attenuated by the object:

    P = n * (A * L * T' + S') + R,     T' the trues an ideal scanner would see,

with n the bin's normalization (crystal efficiencies and geometry), A the attenuation factor
exp(-mu * path), L the live fraction (dead time), S' the scatter as an ideal scanner would see it.
The corrected bin is then

    T' = ((P - R) / (n * L) - S') / A,

and decay correction scales a frame to the activity at a reference time. Each function below gives
one of R, n, S', A, L or the decay factor; the measurement measurements/ch27 checks each against the
simulator's truth.
"""
import numpy as np

from . import sinogram as sg

PS = 1e-12
# Water at 511 keV: 0.0960 cm^2/g, log-log between NIST XCOM's 500 and 600 keV values with
# coherent scattering (0.09687 and 0.08956), as the simulator uses (sim/physics.hpp).
MU_WATER_PER_MM = 0.00960


# [snippet:randoms]
def randoms_from_singles(singles_per_crystal, window_ps, seconds, header, max_ring_difference=None,
                         in_coincidence=None):
    """Expected randoms per bin from each crystal's singles in the energy window: for two crystals
    with singles rates s_a and s_b and a coincidence window tau, R_ab = 2 tau s_a s_b per second,
    so 2 tau S_a S_b / t counts in a run of t seconds with S_a and S_b singles. Summed over the
    ring pairs and the transaxial pair of each bin.

    in_coincidence: each crystal's prompt coincidences (its fan sum in the list mode), subtracted
    from its singles first. A single already paired with its true partner cannot also make a
    random pair: its window becomes a multiple, which the sorter discards (kill all), or it is
    inside its partner's window and opens none. Without the subtraction the estimate counts randoms
    the sorter could never have recorded (measurements/ch27: 31% too many at 20 MBq; the same idea
    as the correction of Stearns et al., IEEE NSS 2003)."""
    mrd = header.max_ring_difference if max_ring_difference is None else max_ring_difference
    s = np.asarray(singles_per_crystal, dtype=np.float64)
    if in_coincidence is not None:
        s = s - np.asarray(in_coincidence, dtype=np.float64).ravel()
    s = s.reshape(sg.RINGS, sg.CRYSTALS_PER_RING)
    ti, tj = sg.crystal_pairs(header)
    ok = ti >= 0
    out = sg.axial_sum(s[:, np.where(ok, ti, 0)], s[:, np.where(ok, tj, 0)], mrd)
    out *= ok
    return 2.0 * window_ps * PS * out / seconds
# [/snippet:randoms]


# [snippet:fansum]
def fan_sums(crystal_a, crystal_b, weight=None):
    """Each crystal's fan sum: the (weighted) coincidences it is an end of."""
    n = sg.RINGS * sg.CRYSTALS_PER_RING
    return (np.bincount(crystal_a, weight, n) + np.bincount(crystal_b, weight, n)).reshape(
        sg.RINGS, sg.CRYSTALS_PER_RING)


def crystal_efficiencies(crystal_a, crystal_b, delayed):
    """Each crystal's relative efficiency from a normalization scan of a source that every crystal
    of a ring sees alike (a long cylinder centered on the axis): the prompts minus the delayeds of
    its fan, over the mean of its ring's. Within a ring the fans differ only by the crystal's own
    efficiency and the mean of its partners', and a fan has thousands of partners, so their mean
    is the same for every crystal to well under 0.1%. Differences between rings are geometry, left
    to the geometric factors. Shape (rings, crystals per ring), mean 1 in every ring."""
    w = np.where(delayed, -1.0, 1.0)
    f = fan_sums(crystal_a, crystal_b, w)
    return f / f.mean(axis=1, keepdims=True)
# [/snippet:fansum]


def efficiency_products(eff, header, max_ring_difference=None):
    """For every bin, the mean over its ring pairs of eff[ring_a, i] * eff[ring_b, j]."""
    mrd = header.max_ring_difference if max_ring_difference is None else max_ring_difference
    ti, tj = sg.crystal_pairs(header)
    ok = ti >= 0
    e = np.asarray(eff, dtype=np.float64)
    out = sg.axial_sum(e[:, np.where(ok, ti, 0)], e[:, np.where(ok, tj, 0)], mrd)
    pairs = sg.ring_pairs_per_slice(mrd)[:, None, None]
    return np.where(ok & (pairs > 0), out / np.maximum(pairs, 1), 0.0)


def cylinder_chords(header, radius_mm):
    """The length in mm of each column's line through a disc of radius_mm centered on the axis:
    a centered uniform cylinder's projection, the same in every view."""
    s = header.s_mm
    return 2.0 * np.sqrt(np.clip(radius_mm ** 2 - s ** 2, 0.0, None))


# [snippet:geometric]
def geometric_factors(norm_scan, eff_products, header, source_radius_mm, min_chord_mm=20.0):
    """The geometric component of the normalization, per (slice, column): what remains of a
    normalization scan (prompts minus randoms) once the crystal efficiencies are divided out and
    the source's own projection (its chords) too, averaged over the views. It holds the solid
    angle, the crystals' depth and angle of incidence and the axial acceptance of each slice, which
    are the same in every view of a ring scanner. Columns where the source's chord is shorter than
    min_chord_mm (the edge of the source) take the factor of the nearest column inside it."""
    chord = cylinder_chords(header, source_radius_mm)
    good = chord >= min_chord_mm
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(eff_products > 0, norm_scan / eff_products, 0.0).sum(axis=1)
        ratio /= np.maximum((eff_products > 0).sum(axis=1), 1)
        g = np.where(good, ratio / np.where(good, chord, 1.0), 0.0)
    cols = np.flatnonzero(good)
    nearest = cols[np.abs(np.arange(header.radial_bins)[:, None] - cols[None, :]).argmin(axis=1)]
    g = np.clip(g[:, nearest], 0.0, None)  # the outermost columns of the end slices: noise below 0
    return g / g[g > 0].mean()
# [/snippet:geometric]


def normalization(eff_products, geometric):
    """The normalization n of every bin: efficiencies times geometry (the data are divided by
    it)."""
    return eff_products * geometric[:, None, :]


# [snippet:attenuation]
def attenuation_factors(header, radius_mm, mu_per_mm=MU_WATER_PER_MM, max_ring_difference=None):
    """A for every bin of a water cylinder of radius_mm centered on the axis and longer than the
    axial field of view, as a calculated attenuation correction would model the head: the mean over
    the bin's ring pairs of exp(-mu L), where L is the transaxial chord stretched by the line's
    axial slope."""
    mrd = header.max_ring_difference if max_ring_difference is None else max_ring_difference
    chord = cylinder_chords(header, radius_mm)                      # transaxial, per column
    span = 2.0 * np.sqrt(sg.RADIUS_MM ** 2 - header.s_mm ** 2)      # crystal to crystal, transaxial
    out = np.zeros((2 * sg.RINGS - 1, header.radial_bins))
    for ra in range(sg.RINGS):
        for rb in range(max(0, ra - mrd), min(sg.RINGS, ra + mrd + 1)):
            dz = (ra - rb) * sg.AXIAL_PITCH_MM
            out[ra + rb] += np.exp(-mu_per_mm * chord * np.sqrt(1.0 + (dz / span) ** 2))
    pairs = sg.ring_pairs_per_slice(mrd)[:, None]
    out = np.where(pairs > 0, out / np.maximum(pairs, 1), 1.0)  # a slice with no ring pair: 1
    return np.broadcast_to(out[:, None, :], (out.shape[0], header.views, header.radial_bins))
# [/snippet:attenuation]


# [snippet:tails]
def tail_fit_scatter(sino, header, object_radius_mm, shape=None, margin_mm=2.0, width_mm=20.0,
                     shared_axes=(1,), sensitivity=None):
    """Scatter by tail fitting. Just outside the object there are no trues, only scatter (and
    randoms, already subtracted): fit the scatter's scale there, and extend the shape under the
    object. The tails are the columns from object_radius_mm + margin_mm to width_mm further out.

    shape: the scatter's shape, broadcastable to sino (from a model of the object: a single
    scatter simulation, or a Monte Carlo of a phantom of its size). None: a Gaussian in s
    centered on the axis, its width fitted to the tails of the sum of all rows, the classic tail
    fit, which needs long tails (measurements/ch27 shows what it does with short ones).
    shared_axes: the axes whose rows share one scale (default the views of a slice): one view of
    one slice holds about one count in its tails, too few for a scale of its own.
    sensitivity: what sino was divided by (the normalization n of each bin), or None for counts.
    The scale is the Poisson maximum likelihood, the counts in the tails over the counts the shape
    predicts there. A least-squares fit to sino / n would weight a bin of the axial ends, n of a
    few percent, as much as a central one: it holds 0 counts most of the time and 1 / n now and
    then, and the fit came out 22% low (measurements/ch27).
    Returns (the scatter estimate, of sino's shape; the Gaussian's sigma or None)."""
    s = header.s_mm
    edge = object_radius_mm + margin_mm
    tails = (np.abs(s) >= edge) & (np.abs(s) <= min(edge + width_mm, header.fov_radius_mm))
    sigma = None
    if shape is None:
        total = sino.reshape(-1, sino.shape[-1]).sum(axis=0)
        y = total[tails]
        keep = y > 0
        # A line fitted to log(total) against s^2 on the tails, the points weighted by their
        # counts (Guo's weights, as in tools/calib).
        slope = np.polyfit(s[tails][keep] ** 2, np.log(y[keep]), 1, w=np.sqrt(y[keep]))[0]
        sigma = float(np.sqrt(-0.5 / slope)) if slope < 0 else float("inf")
        shape = np.exp(-0.5 * (s / sigma) ** 2)
    shape = np.broadcast_to(np.asarray(shape, dtype=np.float64), sino.shape)
    n = np.broadcast_to(1.0 if sensitivity is None else np.asarray(sensitivity, np.float64),
                        sino.shape)
    num = (sino[..., tails] * n[..., tails]).sum(axis=(-1, *shared_axes), keepdims=True)
    den = (shape[..., tails] * n[..., tails]).sum(axis=(-1, *shared_axes), keepdims=True)
    scale = np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)
    return scale * shape, sigma
# [/snippet:tails]


# [snippet:deadtime]
def live_fractions(singles_per_block, seconds, tau_ns, model="non_paralyzable"):
    """Each block's live fraction from its recorded singles rate m (every energy): for a
    non-paralyzable dead time tau the true rate is n = m / (1 - m tau) and the live fraction m / n
    is 1 - m tau. A paralyzable unit's live fraction is exp(-n tau) with m = n exp(-n tau), solved
    for n on the side below the maximum (Chapter 11)."""
    m = np.asarray(singles_per_block, dtype=np.float64) / seconds
    tau = tau_ns * 1e-9
    if model == "non_paralyzable":
        return 1.0 - m * tau
    if model != "paralyzable":
        raise ValueError(f"unknown dead-time model {model!r}")
    n = m.copy()
    for _ in range(100):  # fixed point n = m exp(n tau), which converges below 1 / tau
        n = m * np.exp(n * tau)
    return m / n


def pair_live_fraction(live):
    """The mean over all pairs of blocks of the product of their live fractions: the share of the
    coincidences that both blocks of a pair were live for, when the blocks see similar rates."""
    live = np.asarray(live, dtype=np.float64)
    return (live.sum() ** 2 - (live ** 2).sum()) / (live.size * (live.size - 1))
# [/snippet:deadtime]


# [snippet:decay]
def decay_factor(start_s, duration_s, half_life_s):
    """The factor that turns the counts of a frame from start_s to start_s + duration_s (seconds
    after the reference time) into counts at the activity of the reference time: exp(lambda t0)
    for the decay before the frame, times lambda T / (1 - exp(-lambda T)) for the decay during
    it."""
    lam = np.log(2.0) / half_life_s
    x = lam * duration_s
    during = x / -np.expm1(-x) if x > 0 else 1.0
    return np.exp(lam * start_s) * during
# [/snippet:decay]


# [snippet:compatible]
SETTINGS = ("energy_window_kev", "coincidence_window_ps", "window_mode")


def incompatibilities(norm_record, run_record):
    """Why a normalization scan cannot correct a run, from their run records (.run.json): an
    efficiency measured through another energy window, coincidence window or window mode, or with
    another calibration table, is not the efficiency of the run's data (SRS-COR-003). An empty
    list: the normalization applies."""
    problems = []
    runs = {"normalization": norm_record.get("run") or {}, "run": run_record.get("run") or {}}
    cor = {k: r.get("corrections") for k, r in runs.items()}
    for k, c in cor.items():
        if not isinstance(c, dict) or c.get("format") != 1:
            problems.append(f"the {k}'s record has no corrections object of format 1")
    if problems:
        return problems
    for key in SETTINGS:
        if cor["normalization"].get(key) != cor["run"].get(key):
            problems.append(f"{key}: {cor['normalization'].get(key)} in the normalization, "
                            f"{cor['run'].get(key)} in the run")
    cal = {k: (r.get("calibration") or {}) for k, r in runs.items()}
    ident = {k: (c.get("id", "identity"), c.get("version"), c.get("crc32")) for k, c in cal.items()}
    if ident["normalization"] != ident["run"]:
        problems.append(f"calibration table: {ident['normalization']} in the normalization, "
                        f"{ident['run']} in the run")
    return problems
# [/snippet:compatible]
