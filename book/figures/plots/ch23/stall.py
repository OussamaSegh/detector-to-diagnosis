# SPDX-License-Identifier: MIT
"""Figure for Chapter 23: the longest stall of the receiving thread that a socket buffer absorbs,
against the buffer granted, for the real-time link and for a burst. Bytes charged per datagram
from measurements/ch23/buffer_footprint.txt (2,305 B for a 1,472-byte datagram on loopback).

    python3 book/tools/figures.py build book/figures/plots/ch23/stall.py screen 5 pdf
"""
import sys

import d2d

CHARGED = 2305
RATES = [(4923, "real-time link, 2 MBq: 4,923 datagrams/s", "-"), (470_000, "a burst: 470,000 datagrams/s", "--")]


def main(dst):
    sizes = [2 ** k for k in range(16, 24)]
    fig, ax = d2d.figure(height=2.2, width=0.72)
    for k, (rate, label, ls) in enumerate(RATES):
        ys = [1000 * (2 * g / CHARGED) / rate for g in sizes]
        ax.plot(sizes, ys, color=d2d.PART if k == 0 else d2d.CAT[0], linestyle=ls, marker=d2d.MARKERS[k], markersize=3.5,
                linewidth=d2d.LINE_PT, label=label)
    ax.axhline(8.4, color=d2d.SEM["mistakes"], linewidth=0.9, linestyle=":")
    ax.text(2 ** 16 * 1.1, 8.4 / 1.2, "worst wake-up under load, Chapter 4: 8.4 ms", fontsize=d2d.FONT_PT - 1, va="top")
    ax.axvline(4 * 2 ** 20, color=d2d.MUTED, linewidth=0.8)
    ax.text(4 * 2 ** 20 * 0.92, 0.15, "rmem_max here: 4 MiB", rotation=90, ha="right", va="bottom", fontsize=d2d.FONT_PT - 1.2, color=d2d.MUTED)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(sizes)
    ax.set_xticklabels(["64 KiB", "128", "256", "512", "1 MiB", "2", "4", "8 MiB"])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    ax.set_xlabel("receive buffer granted")
    ax.set_ylabel("longest stall absorbed (ms)")
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
