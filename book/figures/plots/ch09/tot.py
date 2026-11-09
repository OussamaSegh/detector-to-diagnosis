# SPDX-License-Identifier: MIT
"""Chapter 9: time over threshold (ToT), on the pulse model of Exercise 9.4. Left: three pulses
and how long each stays above the threshold. Right: ToT against energy is logarithmic: every
doubling of the energy adds the same 27.7 ns."""
import math
import pathlib
import sys

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "exercises/ch09/e4_time_walk/solution"))
import time_walk as tw  # noqa: E402

THR = 0.02
fig, (a1, a2) = d2d.figure(height=2.3, ncols=2, gridspec_kw={"width_ratios": [1.15, 1]})
ts = [i * 0.5 for i in range(0, 401)]
for i, kev in enumerate((100, 250, 511)):
    a = kev / 511
    c = d2d.CAT[i]
    a1.plot(ts, [tw.pulse(t, a) for t in ts], color=c, linestyle=d2d.DASHES[i], label=f"{kev} keV")
    tot = tw.time_over_threshold_ns(THR, a)
    t0 = tw.leading_edge_ns(THR, a)
    y = -0.06 - 0.06 * i
    a1.annotate("", xy=(t0 + tot, y), xytext=(t0, y), arrowprops=dict(arrowstyle="<->", color=c, lw=1.1))
    a1.text(t0 + tot + 3, y, f"{tot:.0f} ns", color=c, va="center", fontweight="bold")
a1.axhline(THR, color=d2d.PART, linestyle="--", linewidth=1)
a1.text(150, THR + 0.03, "threshold", color=d2d.PART, fontweight="bold")
a1.set_xlim(0, 210)
a1.set_ylim(-0.25, 1.05)
a1.set_xlabel("time (ns)")
a1.set_ylabel("amplitude (511 keV = 1)")
a1.set_title("How long each pulse stays above")
a1.legend(loc="upper right")
es = [20 * 1.05 ** k for k in range(0, 75) if 20 * 1.05 ** k <= 700]
a2.plot(es, [tw.time_over_threshold_ns(THR, e / 511) for e in es], color=d2d.PART)
for e in (100, 200, 400):
    t = tw.time_over_threshold_ns(THR, e / 511)
    a2.plot([e], [t], marker="o", color=d2d.PART)
    a2.annotate(f"{e} keV: {t:.0f} ns", (e, t), xytext=(6, -12), textcoords="offset points")
a2.set_xlabel("deposited energy (keV)")
a2.set_ylabel("time over threshold (ns)")
a2.set_title(f"Each doubling adds {40 * math.log(2):.1f} ns")
a2.set_xlim(0, 700)
fig.tight_layout(w_pad=2)
d2d.save(fig)
