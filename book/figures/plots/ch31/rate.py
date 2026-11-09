# SPDX-License-Identifier: MIT
"""Figure for Chapter 31: is the rate constant? A synthetic run of 200 bins of about 1,000 prompts,
drawn with a fixed seed, once constant and once with one bin that lost a block of 160; the p-values
are those of the package's own check_rate (analysis/src/minidaq_analysis/rates.py).

    python3 book/tools/figures.py build book/figures/plots/ch31/rate.py screen 7 pdf analysis/src/minidaq_analysis/rates.py
"""
import pathlib
import sys

import numpy as np

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis/src"))
from minidaq_analysis import rates  # noqa: E402


def main(dst):
    rng = np.random.default_rng(31)
    good = rng.poisson(1000, 201).astype(np.int64)
    bad = good.copy()
    bad[120] -= 160
    fig, axes = d2d.figure(height=2.1, width=1.0, nrows=2, sharex=True)
    for ax, counts, title in zip(axes, (good, bad), ("constant", "one bin lost a block of 160 prompts")):
        chk = rates.check_rate(counts[:-1])
        x = np.arange(counts.size - 1) * 10
        ax.plot(x, counts[:-1], color=d2d.PART if counts is good else d2d.CAT[0], lw=0.8, drawstyle="steps-post")
        m = counts[:-1].mean()
        ax.axhspan(m - 3 * np.sqrt(m), m + 3 * np.sqrt(m), color=d2d.tint(d2d.MUTED, 0.15), lw=0)
        ax.set_ylim(760, 1180)
        ax.text(1.0, 1.02, f"{title}:  p constant {chk.p_constant:.3f},  p dip {chk.p_dip:.2g}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=d2d.FONT_PT - 1.1, color=d2d.INK)
        ax.set_ylabel("per 10 ms", fontsize=d2d.FONT_PT - 1)
    axes[1].annotate("the dip", (1200, bad[120]), xytext=(1400, 820), fontsize=d2d.FONT_PT - 1, color=d2d.CAT[0],
                     arrowprops={"arrowstyle": "-", "color": d2d.MUTED, "lw": 0.6})
    axes[1].set_xlabel("time in the run, ms (shaded: mean plus or minus 3 SD)")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
