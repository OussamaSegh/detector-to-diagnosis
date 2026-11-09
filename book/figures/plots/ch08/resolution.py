# SPDX-License-Identifier: MIT
"""Chapter 8: the spatial resolution budget at the center of the ring (Moses 2011 form,
R = 1.25 sqrt((d/2)^2 + (0.0022 D)^2 + r^2)), for the 30 cm brain ring with 2.45 mm crystals
and for an 80 cm whole-body ring with the same crystals."""
import math

import d2d

cases = [("30 cm ring,\n2.45 mm crystals", 2.45, 300), ("80 cm ring,\nsame crystals", 2.45, 800)]
r = 0.2  # positron range of fluorine-18, as in the chapter (an assumption)
fig, ax = d2d.figure(height=1.9, width=0.95)
for i, (name, d, D) in enumerate(cases):
    terms = [("crystal size d/2", d / 2), ("non-collinearity 0.0022 D", 0.0022 * D), ("positron range", r)]
    left = 0
    for j, (tname, v) in enumerate(terms):
        w = v * v
        ax.barh(i, w, left=left, color=d2d.CAT[j], hatch=["", "///", "..."][j], edgecolor="white",
                label=tname if i == 0 else None, height=0.55)
        left += w
    total = 1.25 * math.sqrt(left)
    ax.text(left + 0.1, i, f"R ≈ 1.25·√{left:.2f} = {total:.2f} mm", va="center", fontweight="bold")
ax.set_yticks([0, 1], [c[0] for c in cases])
ax.invert_yaxis()
ax.set_xlabel("contribution to R² / 1.25² (mm²): the terms add in quadrature")
ax.set_xlim(0, 8)
ax.legend(loc="lower right", ncols=3, bbox_to_anchor=(1.0, 1.0))
ax.grid(axis="y", visible=False)
d2d.save(fig)
