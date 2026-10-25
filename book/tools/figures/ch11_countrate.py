# SPDX-License-Identifier: MIT
"""Figure for Chapter 11: NEMA-style count-rate curves from
measurements/ch11/countrate.txt. Left: trues, scatters and randoms without
dead time and with the 1 us non-paralyzable block dead time. Right: NECR for
the three front ends, k = 1 solid and k = 2 dashed.

    python3 book/tools/figures/ch11_countrate.py book/src/img/ch11-countrate.png
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "../../../measurements/ch11/countrate.txt")
MODELS = {  # section title prefix -> (color, label)
    "no dead time": ("#1f5fa8", "no dead time"),
    "non-paralyzable": ("#c0392b", "non-paralyzable 1 µs"),
    "paralyzable": ("#7a9a3a", "paralyzable 1 µs"),
}


def read_table():
    """section -> list of (MBq, trues, scatters, randoms, necr1, necr2)."""
    rows, section = {}, None
    for line in open(SRC, encoding="utf-8"):
        if line.startswith("== "):
            section = next(k for k in MODELS if line[3:].startswith(k))
            rows[section] = []
            continue
        f = line.split()
        if section and f and f[0].isdigit():
            rows[section].append((float(f[0]), float(f[4]), float(f[5]), float(f[6]), float(f[9]), float(f[10])))
    return rows


def main(dst):
    rows = read_table()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.4, 2.9), dpi=200)
    for section, style in (("no dead time", "-"), ("non-paralyzable", "--")):
        pts = rows[section]
        x = [p[0] for p in pts]
        for col, color, name in ((1, "#1f5fa8", "trues"), (2, "#e08a2b", "scatters"), (3, "#c0392b", "randoms")):
            ax1.plot(x, [p[col] / 1e3 for p in pts], style, color=color, linewidth=1.0,
                     label=name if style == "-" else None)
    ax1.plot([], [], "--", color="gray", linewidth=1.0, label="1 µs non-paralyzable")
    ax1.set_yscale("log")
    ax1.set_ylabel("rate (k/s)", fontsize=8)
    ax1.set_title("prompts by truth", fontsize=9)
    ax1.legend(fontsize=6.5, frameon=False)
    for section, (color, label) in MODELS.items():
        pts = rows[section]
        x = [p[0] for p in pts]
        ax2.plot(x, [p[4] / 1e3 for p in pts], "-", marker="o", markersize=2.5, color=color, linewidth=1.0,
                 label=label)
        ax2.plot(x, [p[5] / 1e3 for p in pts], "--", color=color, linewidth=0.8)
    ax2.plot([], [], "--", color="gray", linewidth=0.8, label="k = 2")
    ax2.set_ylabel("NECR (k/s)", fontsize=8)
    ax2.set_title("noise-equivalent count rate", fontsize=9)
    ax2.legend(fontsize=6.5, frameon=False)
    for ax in (ax1, ax2):
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 20, 50, 100, 200, 500, 1000])
        ax.set_xticklabels(["5", "10", "20", "50", "100", "200", "500", "1000"], fontsize=7)
        ax.set_xlabel("activity (MBq)", fontsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1])
