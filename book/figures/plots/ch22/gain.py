# SPDX-License-Identifier: MIT
"""Figure for Chapter 22: SiPM gain against temperature at a fixed bias and with the bias following
the temperature, from the chapter's model (breakdown 38 V at 25 C, 34 mV/C, overvoltage 2.7 V,
5 mV dead band; Hamamatsu S14160-3050HS datasheet values).

    python3 book/tools/figures.py build book/figures/plots/ch22/gain.py screen 5 pdf
"""
import sys

import d2d

VBD25, K, VOV, DEAD = 38.0, 0.034, 2.7, 0.005


def main(dst):
    ts = [20 + 0.01 * i for i in range(2101)]
    fixed = [100 * (VBD25 + VOV - (VBD25 + K * (t - 25))) / VOV for t in ts]
    comp, set_v = [], VBD25 + VOV + K * (ts[0] - 25)
    for t in ts:
        want = VBD25 + K * (t - 25) + VOV
        if abs(want - set_v) >= DEAD:
            set_v = want
        comp.append(100 * (set_v - (VBD25 + K * (t - 25))) / VOV)
    fig, ax = d2d.figure(height=2.1, width=0.72)
    ax.axvspan(35, 40, color=d2d.tint(d2d.CAT[1], 0.15), linewidth=0)
    ax.axvspan(40, 41, color=d2d.tint(d2d.SEM["mistakes"], 0.2), linewidth=0)
    ax.plot(ts, fixed, color=d2d.MUTED, linestyle="--", linewidth=d2d.LINE_PT, label="fixed bias, 40.7 V")
    ax.plot(ts, comp, color=d2d.PART, linewidth=d2d.LINE_PT, label="bias follows the temperature")
    ax.text(37.5, 112, "warning", ha="center", fontsize=d2d.FONT_PT - 1)
    ax.text(40.5, 112, "alarm", ha="center", fontsize=d2d.FONT_PT - 1, rotation=90, va="bottom")
    ax.annotate("1.3% of gain per degree", xy=(30, fixed[1000]), xytext=(21, 78), fontsize=d2d.FONT_PT - 0.8,
                arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.6})
    ax.set_xlim(20, 41)
    ax.set_ylim(60, 125)
    ax.set_xlabel("SiPM temperature (°C)")
    ax.set_ylabel("gain (% of nominal)")
    ax.legend(loc="lower left", fontsize=d2d.FONT_PT - 0.9, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
