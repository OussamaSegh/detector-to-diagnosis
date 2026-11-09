# SPDX-License-Identifier: MIT
"""Figure for Chapter 4: cyclictest's wake-up latency histograms on the book's VM, from
measurements/ch04/cyclictest/*.txt (30 s at 200 us on CPU 1, idle and under stress-ng).

    python3 book/tools/figures.py build book/figures/plots/ch04/cyclictest.py screen 1 pdf
"""
import os
import sys

import numpy as np

import d2d

DIR = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch04/cyclictest")
RUNS = (("idle_other", "idle, normal", 0, "-"), ("idle_fifo", "idle, SCHED_FIFO 80", 2, "--"),
        ("load_other", "load, normal", 3, "-."), ("load_fifo", "load, SCHED_FIFO 80", 0, ":"))


def read(name):
    h = np.zeros(20000)
    for line in open(os.path.join(DIR, name + ".txt"), encoding="utf-8"):
        f = line.split()
        if len(f) == 2 and f[0].isdigit():
            h[int(f[0])] = int(f[1])
    return h


def main(dst):
    fig, ax = d2d.figure(height=2.5, width=0.85)
    for k, (name, label, c, ls) in enumerate(RUNS):
        h = read(name)
        surv = 1 - np.cumsum(h) / h.sum()
        x = np.arange(len(h))
        ok = surv > 0
        ax.step(x[ok], surv[ok], where="post", color=d2d.CAT[c] if k != 3 else d2d.PART,
                linestyle=ls, linewidth=1.2, label=label)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(5, 20000)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("wake-up latency (µs)")
    ax.set_ylabel("share of wake-ups later than this")
    ax.legend(loc="lower left")
    ax.set_ylim(5e-6, 1.5)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
