# SPDX-License-Identifier: MIT
"""Chapter 9: watching two boards' clocks from the data. The peak of t_B - t_A for true
coincidences between two boards, per one-second slice, for a drift of 1 ns per second (an
illustration: Gaussian peaks of 300 ps FWHM on a flat randoms background, seeded)."""
import random

import d2d

rng = random.Random(9)
fig, ax = d2d.figure(height=2.1, width=0.85)
bins = [-1500 + 20 * i for i in range(0, 226)]
for s in range(4):
    off = 1000 * s - 600
    vals = [rng.gauss(off, 300 / 2.355) for _ in range(4000)] + [rng.uniform(-1500, 3000) for _ in range(900)]
    h = [0] * (len(bins) - 1)
    for v in vals:
        k = int((v + 1500) // 20)
        if 0 <= k < len(h):
            h[k] += 1
    c = d2d.CAT[s]
    ax.step([b + 10 for b in bins[:-1]], h, where="mid", color=c, linestyle=d2d.DASHES[s])
    ax.text(off, max(h) + 8, f"{s + 1}", color=c, ha="center", fontweight="bold")
ax.set_xlabel("t_B − t_A (ps)")
ax.set_ylabel("pairs per 20 ps")
ax.set_xlim(-1500, 3000)
ax.text(-1450, 255, "number over a peak:\nthe second of the run", ha="left", va="top", color=d2d.MUTED)
d2d.save(fig)
