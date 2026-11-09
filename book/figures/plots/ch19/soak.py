# SPDX-License-Identifier: MIT
"""Figure for Chapter 19: the 30-minute soak, resident memory with the fitted trend and p99 latency
per 10 s interval, from measurements/ch19/soak/samples.csv.

    python3 book/tools/figures.py build book/figures/plots/ch19/soak.py screen 4 pdf measurements/ch19/soak
"""
import csv
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch19/soak/samples.csv"
WARMUP_S = 600


def main(dst):
    rows = list(csv.DictReader(SRC.open()))
    t = [float(r["t_s"]) / 60 for r in rows]
    rss = [int(r["rss_kib"]) / 1024 for r in rows]
    p99 = [float(r["p99_ms"]) for r in rows]
    fig, (a, b) = d2d.figure(height=2.5, width=0.9, nrows=2, sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    for ax in (a, b):
        ax.axvspan(0, WARMUP_S / 60, color=d2d.tint(d2d.MUTED, 0.15), linewidth=0)
    a.plot(t, rss, color=d2d.PART, linewidth=d2d.LINE_PT)
    xs = [x for x in t if x * 60 >= WARMUP_S]
    ys = [y for x, y in zip(t, rss) if x * 60 >= WARMUP_S]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a.plot([xs[0], xs[-1]], [my + slope * (xs[0] - mx), my + slope * (xs[-1] - mx)], color=d2d.CAT[1], linestyle="--", linewidth=1.2)
    a.text(xs[-1], my + 0.15, f"trend {slope * 60:+.3f} MiB/h (limit 1 MiB/h)", ha="right", va="bottom", fontsize=d2d.FONT_PT - 0.8)
    a.set_ylabel("resident\nmemory (MiB)")
    a.set_ylim(29, 31.5)
    a.text(0.3, 29.15, "warm-up, not judged", fontsize=d2d.FONT_PT - 1.0, va="bottom")
    b.plot(t[1:], p99[1:], color=d2d.CAT[0], linewidth=0.9, marker="o", markersize=1.6)
    b.set_yscale("log")
    b.set_ylabel("p99 latency\nper 10 s (ms)")
    b.set_xlabel("minutes at 1,000,000 singles/s (no losses, no faults)")
    b.set_yticks([1, 2, 5, 10, 20])
    b.yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    b.yaxis.set_minor_formatter(lambda v, _: "")
    b.text(29.5, max(p99) * 0.8, "outliers: the machine was compiling", ha="right", va="top", fontsize=d2d.FONT_PT - 1.0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
