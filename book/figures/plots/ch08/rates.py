# SPDX-License-Identifier: MIT
"""Chapter 8: how the rates scale with activity. Trues and scatters grow with A, randoms with A^2.
Scaled from the 5 MBq simulation in the chapter's table (435 to 650 keV, 4 ns window); dead time
is left out here (Chapter 11)."""
import d2d

T5, S5, R5 = 47362, 17098, 3007
acts = [i * 0.5 for i in range(1, 81)]
t = [T5 * a / 5 for a in acts]
s = [S5 * a / 5 for a in acts]
r = [R5 * (a / 5) ** 2 for a in acts]

fig, ax = d2d.figure(height=2.4, width=0.75)
for i, (y, name) in enumerate(((t, "trues ∝ A"), (s, "scatters ∝ A"), (r, "randoms ∝ A²"))):
    ax.plot(acts, [v / 1000 for v in y], color=d2d.CAT[i], linestyle=d2d.DASHES[i])
    d2d.label(ax, acts[-1] + 0.6, y[-1] / 1000, name, c=d2d.CAT[i], va="center")
ax.plot([5], [T5 / 1000], marker="o", color=d2d.CAT[0])
ax.plot([5], [S5 / 1000], marker="s", color=d2d.CAT[1])
ax.plot([5], [R5 / 1000], marker="^", color=d2d.CAT[2])
ax.annotate("simulated at 5 MBq", (5, T5 / 1000), xytext=(8, 40), textcoords="offset points",
            arrowprops=dict(arrowstyle="-", color=d2d.MUTED, lw=0.6))
ax.set_xlabel("activity A (MBq)")
ax.set_ylabel("rate (thousands per second)")
ax.set_xlim(0, 40)
ax.set_ylim(0, None)
d2d.save(fig)
