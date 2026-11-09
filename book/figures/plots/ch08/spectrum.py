# SPDX-License-Identifier: MIT
"""Chapter 8: the energy spectrum of simulated singles, by truth (measurements/ch08/spectrum.txt)."""
import pathlib

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
rows = [list(map(int, line.split())) for line in (ROOT / "measurements/ch08/spectrum.txt").read_text().splitlines()
        if line and not line.startswith("#")]
x = [r[0] + 5 for r in rows]
direct = [r[1] for r in rows]
scat = [r[2] for r in rows]

fig, ax = d2d.figure(height=2.5)
ax.bar(x, direct, width=10, color=d2d.CAT[0], label="photon not scattered in the phantom", linewidth=0)
ax.bar(x, scat, width=10, bottom=direct, color=d2d.CAT[1], hatch="////", edgecolor="white",
       label="photon scattered in the phantom", linewidth=0)
ax.axvspan(435, 650, color=d2d.tint(d2d.PART, 0.10), zorder=0)
for e in (435, 650):
    ax.axvline(e, color=d2d.PART, linestyle="--", linewidth=1.0)
top = max(a + b for a, b in zip(direct, scat))
ax.text(655, top * 0.62, "energy window\n435 to 650 keV", color=d2d.PART, fontweight="bold")
ax.annotate("photopeak, 511 keV\n(12% resolution)", xy=(511, top * 0.98), xytext=(330, top * 0.9),
            arrowprops=dict(arrowstyle="-", color=d2d.MUTED, lw=0.6))
ax.annotate("Compton edge, 341 keV", xy=(341, direct[34] * 1.05), xytext=(130, top * 0.55),
            arrowprops=dict(arrowstyle="-", color=d2d.MUTED, lw=0.6))
ax.set_xlabel("measured energy (keV)")
ax.set_ylabel("singles per 10 keV")
ax.set_xlim(0, 800)
ax.legend(loc="upper left")
ax.grid(axis="x", visible=False)
d2d.save(fig)
