# SPDX-License-Identifier: MIT
"""Figure for Chapter 4: coordinated omission, the deterministic case of Exercise 4.6. Requests
due every 1 ms, each served in 100 us, one stall of 200 ms. Measured from when each request
was sent (naive) and from when it was due (corrected).

    python3 book/tools/figures.py build book/figures/plots/ch04/omission.py screen 1 pdf
"""
import sys

import numpy as np

import d2d


def simulate(n=10000, period=1.0, service=0.1, stall_at=5000, stall=200.0):
    due = np.arange(n) * period
    naive, corrected, free = np.empty(n), np.empty(n), 0.0
    for i in range(n):
        start = max(due[i], free)
        s = stall if i == stall_at else service
        free = start + s
        naive[i] = s
        corrected[i] = free - due[i]
    return naive, corrected


def main(dst):
    naive, corrected = simulate()
    i = np.arange(len(naive))
    fig, ax = d2d.figure(height=2.3, width=0.8)
    sel = (i > 4950) & (i < 5260)
    ax.plot(i[sel], corrected[sel], color=d2d.PART, linewidth=1.4, label="from when it was due (corrected)")
    ax.plot(i[sel], naive[sel], color=d2d.CAT[3], linestyle="--", linewidth=1.2, label="from when it was sent (naive)")
    for name, v, y in (("naive", naive, 0.3), ("corrected", corrected, 0.2)):
        ax.text(0.2, y, f"{name}: p99 = {np.percentile(v, 99):.1f} ms", transform=ax.transAxes, ha="left",
                fontsize=d2d.FONT_PT - 0.6)
    ax.set_yscale("log")
    ax.set_ylim(0.05, 600)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("request number (one every 1 ms; the stall is at request 5,000)")
    ax.set_ylabel("latency (ms)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
