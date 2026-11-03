# SPDX-License-Identifier: MIT
"""Exercise 27.3: calculated attenuation of an elliptical head outline, and the decay of a frame.

A line of response is given by its angle phi and its signed distance s from the center of the
field of view: the points p with p . (cos phi, sin phi) = s. Lengths are in mm.
"""
import numpy as np


# [snippet:ellipse]
def chords(s_mm, phi, a_mm, b_mm, center_mm=(0.0, 0.0), angle=0.0):
    """The length of each line (s_mm, phi, broadcast together) inside the ellipse with semi-axes
    a_mm along its own x and b_mm along its own y, centered at center_mm and turned by angle.

    In the ellipse's frame the line has the normal (cos(phi - angle), sin(phi - angle)) and the
    distance s - center . (cos phi, sin phi). The ellipse reaches h = sqrt(a^2 n_x^2 + b^2 n_y^2)
    along that normal, and a line at distance d < h cuts it in 2 a b sqrt(h^2 - d^2) / h^2."""
    s = np.asarray(s_mm, dtype=float)
    phi = np.asarray(phi, dtype=float)
    d = s - (center_mm[0] * np.cos(phi) + center_mm[1] * np.sin(phi))
    nx, ny = np.cos(phi - angle), np.sin(phi - angle)
    h2 = (a_mm * nx) ** 2 + (b_mm * ny) ** 2
    return 2.0 * a_mm * b_mm * np.sqrt(np.clip(h2 - d ** 2, 0.0, None)) / h2
# [/snippet:ellipse]


def acf(chord_mm, mu_per_cm=0.096):
    """The attenuation correction factor of a line, exp(mu L): both photons of a pair together
    cross the whole chord, wherever on the line the annihilation was. mu in 1/cm, L in mm."""
    return np.exp(mu_per_cm * np.asarray(chord_mm, dtype=float) / 10.0)


# [snippet:decay]
def decay_factor(start_s, duration_s, half_life_s):
    """The factor that turns the counts of a frame from start_s to start_s + duration_s (seconds
    after the reference time) into counts at the activity of the reference time."""
    lam = np.log(2.0) / half_life_s
    x = lam * duration_s
    during = x / -np.expm1(-x) if x > 0 else 1.0
    return np.exp(lam * start_s) * during
# [/snippet:decay]
