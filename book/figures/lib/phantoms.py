# SPDX-License-Identifier: MIT
"""Synthetic phantoms for the book's figures (roadmap 2.3.0, Theme I). Not a patient, not an
atlas: ellipses whose sizes and values are typical of a head, chosen for teaching.

brain(xs, ys) returns (activity, mu): the tracer's relative uptake and the linear attenuation
coefficient at 511 keV in 1/mm (water 0.0096, bone about 0.0172), on the pixel centers xs, ys
in mm. Gray matter takes up about four times as much as white matter (an FDG-like contrast); the
ventricles take up almost nothing; one small lesion is twice as hot as gray matter.
"""
import numpy as np

MU_WATER = 0.0096
MU_BONE = 0.0172


def _ellipse(xs, ys, cx, cy, a, b, angle=0.0):
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    u = (xs - cx) * c + (ys - cy) * s
    v = -(xs - cx) * s + (ys - cy) * c
    return (u / a) ** 2 + (v / b) ** 2 <= 1.0


def brain(xs, ys):
    head = _ellipse(xs, ys, 0, 0, 72, 90)
    skull = head & ~_ellipse(xs, ys, 0, 0, 66, 84)
    brain_ = _ellipse(xs, ys, 0, 0, 64, 82)
    white = _ellipse(xs, ys, 0, 2, 50, 66)
    act = np.zeros_like(xs, dtype=float)
    act[head] = 0.15                 # scalp and skull: little uptake
    act[brain_] = 4.0                # cortex: gray matter
    act[white] = 1.0                 # white matter
    for sx in (-1, 1):               # deep gray matter (striatum), ventricles between
        act[_ellipse(xs, ys, sx * 21, 2, 6, 15, sx * 12)] = 4.0
        act[_ellipse(xs, ys, sx * 6, 4, 3.5, 17, sx * 10)] = 0.1
    act[_ellipse(xs, ys, 30, 40, 6, 6)] = 8.0                     # a small lesion
    mu = np.zeros_like(xs, dtype=float)
    mu[head] = MU_WATER
    mu[skull] = MU_BONE
    return act, mu
