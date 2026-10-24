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


def leading_edge_ns(threshold, amplitude):
    """When the rising edge first crosses a fixed threshold (None: never).

    TODO(9.4): a scan in 50 ps steps, like a slow digitizer. The tests need
    the crossing to better than 1 ps.
    """
    t = 0.0
    while t < peak_time_ns():
        if pulse(t, amplitude) >= threshold:
            return t
        t += 0.05
    return None


def constant_fraction_ns(fraction, amplitude):
    """When the rising edge crosses a fixed fraction of the pulse's own peak."""
    raise NotImplementedError("TODO(9.4)")


def walk_ps(timing, energies_kev, reference_kev=511.0):
    """Crossing time at each energy minus the time at the reference, in ps."""
    ref = timing(reference_kev)
    return [(timing(e) - ref) * 1000.0 for e in energies_kev]


def time_over_threshold_ns(threshold, amplitude):
    """How long the pulse stays above the threshold."""
    raise NotImplementedError("TODO(9.4)")
