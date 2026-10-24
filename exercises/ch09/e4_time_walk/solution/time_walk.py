# SPDX-License-Identifier: MIT
"""Exercise 9.4: leading-edge time walk, constant-fraction timing, and why
time over threshold is a nonlinear energy measure.

The pulse model is a difference of exponentials, a common first model of a
scintillator pulse seen by a fast photodetector:

    v(t) = A * (exp(-t / tau_decay) - exp(-t / tau_rise)),  t >= 0

with A proportional to the deposited energy. Times are in nanoseconds.
"""
import math

TAU_RISE_NS = 0.5    # assumption: an illustrative rise time
TAU_DECAY_NS = 40.0  # LYSO decay time, about 40 ns (Chapter 8)


def pulse(t_ns, amplitude):
    if t_ns < 0.0:
        return 0.0
    return amplitude * (math.exp(-t_ns / TAU_DECAY_NS) - math.exp(-t_ns / TAU_RISE_NS))


def peak_time_ns():
    """Where dv/dt = 0: t = ln(tau_d / tau_r) * tau_r * tau_d / (tau_d - tau_r)."""
    return math.log(TAU_DECAY_NS / TAU_RISE_NS) * TAU_RISE_NS * TAU_DECAY_NS / (TAU_DECAY_NS - TAU_RISE_NS)


def _bisect(f, lo, hi, tol_ns=1e-6):
    """A root of f in [lo, hi], where f(lo) < 0 <= f(hi)."""
    while hi - lo > tol_ns:
        mid = 0.5 * (lo + hi)
        if f(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# [snippet:edge]
def leading_edge_ns(threshold, amplitude):
    """When the rising edge first crosses a fixed threshold (None: never)."""
    tp = peak_time_ns()
    if pulse(tp, amplitude) < threshold:
        return None
    return _bisect(lambda t: pulse(t, amplitude) - threshold, 0.0, tp)


def constant_fraction_ns(fraction, amplitude):
    """When the rising edge crosses a fixed fraction of the pulse's own peak.

    For a fixed pulse shape the crossing time does not depend on the
    amplitude: the walk is gone. (An analog CFD reaches the same result by
    subtracting a delayed copy from an attenuated one.)
    """
    return leading_edge_ns(fraction * pulse(peak_time_ns(), amplitude), amplitude)
# [/snippet:edge]


def walk_ps(timing, energies_kev, reference_kev=511.0):
    """Crossing time at each energy minus the time at the reference, in ps."""
    ref = timing(reference_kev)
    return [(timing(e) - ref) * 1000.0 for e in energies_kev]


# [snippet:tot]
def time_over_threshold_ns(threshold, amplitude):
    """How long the pulse stays above the threshold."""
    t_on = leading_edge_ns(threshold, amplitude)
    if t_on is None:
        return 0.0
    tp = peak_time_ns()
    hi = tp
    while pulse(hi, amplitude) >= threshold:  # find a point below on the tail
        hi *= 2.0
    t_off = _bisect(lambda t: threshold - pulse(t, amplitude), tp, hi)
    return t_off - t_on
# [/snippet:tot]
