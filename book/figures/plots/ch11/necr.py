# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: what the NECR means, at 100 MBq without dead time, from
measurements/ch11/countrate.txt. The prompts per second, split by truth, against the
noise-free trues that would give the same signal-to-noise ratio (k = 1 and k = 2).

    python3 book/tools/figures.py build book/figures/plots/ch11/necr.py screen 2 pdf
"""
import os
import sys

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch11/countrate.txt")


def read(mbq=100):
    section = None
    for line in open(SRC, encoding="utf-8"):
        if line.startswith("== "):
            section = line[3:].strip()
            continue
        f = line.split()
        if section == "no dead time" and f and f[0] == str(mbq):
            return float(f[4]), float(f[5]), float(f[6])
    raise SystemExit("necr: row not found")


def main(dst):
    t, s, r = read()
    n1, n2 = t * t / (t + s + r), t * t / (t + s + 2 * r)
    fig, ax = d2d.figure(height=1.65)
    left = 0
    for v, label, c, hatch in ((t, "trues", d2d.CAT[2], ""), (s, "scatters", d2d.CAT[1], "///"),
                               (r, "randoms", d2d.CAT[3], "...")):
        ax.barh(2, v, left=left, color=d2d.tint(c, 0.55), edgecolor=c, hatch=hatch, height=0.6, linewidth=0.8)
        ax.text(left + v / 2, 2, f"{label}\n{v / 1000:.1f} k", ha="center", va="center",
                fontsize=d2d.FONT_PT - 0.8,
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85})
        left += v
    for y, v, k in ((1, n1, 1), (0, n2, 2)):
        ax.barh(y, v, color=d2d.PART, height=0.6, linewidth=0)
        ax.text(v + 2500, y, f"{v / 1000:.1f} k noise-free trues per second", va="center",
                fontsize=d2d.FONT_PT - 0.6)
    ax.set_yticks([2, 1, 0])
    ax.set_yticklabels(["prompts", "NECR, k = 1", "NECR, k = 2"])
    ax.set_xlabel("counts per second at 100 MBq, no dead time")
    ax.set_xlim(0, 215000)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x / 1000:.0f} k")
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
