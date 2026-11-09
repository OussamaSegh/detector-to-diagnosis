# SPDX-License-Identifier: MIT
"""Chapter 8: Compton scattering of a 511 keV photon. Left: the energy it keeps against the
angle, E' = 511 / (2 - cos theta). Right: how likely each angle is (Klein-Nishina, per unit
angle), which favors small angles."""
import math

import d2d

th = [i * 0.5 for i in range(361)]
ep = [511 / (2 - math.cos(math.radians(t))) for t in th]


def kn(t):
    c = math.cos(math.radians(t))
    p = 1 / (2 - c)  # E'/E at 511 keV
    return 0.5 * p * p * (p + 1 / p - (1 - c * c)) * 2 * math.pi * math.sin(math.radians(t))


k = [kn(t) for t in th]
peak = max(k)
k = [v / peak for v in k]

fig, (a, b) = d2d.figure(height=2.2, ncols=2)
a.plot(th, ep, color=d2d.PART)
for t in (25, 90, 180):
    e = 511 / (2 - math.cos(math.radians(t)))
    a.plot([t], [e], marker="o", color=d2d.PART)
    a.annotate(f"{t}°: {e:.0f} keV", (t, e), xytext=(6, 4), textcoords="offset points")
a.axhline(435, color=d2d.CAT[3], linestyle="--", linewidth=1)
a.text(70, 445, "a 435 keV lower threshold", color=d2d.CAT[3])
a.set_xlabel("scattering angle θ (degrees)")
a.set_ylabel("energy kept E′ (keV)")
a.set_xlim(0, 185)
a.set_ylim(150, 530)
a.set_title("Energy after one scatter")
b.fill_between(th, k, color=d2d.tint(d2d.PART, 0.25))
b.plot(th, k, color=d2d.PART)
b.set_xlabel("scattering angle θ (degrees)")
b.set_ylabel("relative probability")
b.set_xlim(0, 185)
b.set_ylim(0, 1.08)
b.set_title("Which angles are likely")
b.text(60, 0.82, "small angles dominate:\nthose photons keep\nmost of their energy")
fig.tight_layout(w_pad=2.5)
d2d.save(fig)
