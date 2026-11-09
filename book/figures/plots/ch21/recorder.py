# SPDX-License-Identifier: MIT
"""Figure for Chapter 21: the flight recorder's cost per event before and after removing the shared
counter, from measurements/ch21/bm_flight_recorder.txt (medians).

    python3 book/tools/figures.py build book/figures/plots/ch21/recorder.py screen 4 pdf measurements/ch21/bm_flight_recorder.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch21/bm_flight_recorder.txt"
CASES = [("BM_TraceRecord/threads:1_median", "one thread"), ("BM_TraceRecord/threads:4_median", "four threads"),
         ("BM_TraceRecordWhileReading_median", "one thread,\nanother reading")]


def parse():
    out, section = {}, None
    for line in SRC.read_text().splitlines():
        if line.startswith("## before"):
            section = "before"
        elif line.startswith("## after"):
            section = "after"
        m = re.match(r"^(BM_\S+)\s+([\d.]+) (ns|us)", line)
        if m and section:
            out[(section, m.group(1))] = float(m.group(2)) * (1000 if m.group(3) == "us" else 1)
    return out


def main(dst):
    d = parse()
    fig, ax = d2d.figure(height=1.9, width=0.7)
    w = 0.38
    for k, (key, label) in enumerate(CASES):
        b, a = d[("before", key)], d[("after", key)]
        ax.bar(k - w / 2, b, w, color=d2d.tint(d2d.SEM["mistakes"], 0.75), hatch="////", edgecolor="white", linewidth=0.3,
               label="one shared counter" if k == 0 else None)
        ax.bar(k + w / 2, a, w, color=d2d.PART, label="per-ring counters, aligned rings" if k == 0 else None)
        ax.text(k - w / 2, b + 4, f"{b:g}", ha="center", fontsize=d2d.FONT_PT - 1)
        ax.text(k + w / 2, a + 4, f"{a:g}", ha="center", fontsize=d2d.FONT_PT - 1)
    ax.axhline(100, color=d2d.INK, linestyle="--", linewidth=0.8, label="SRS-DIAG-005: at most 100 ns")
    ax.axhline(27.8, color=d2d.MUTED, linestyle=":", linewidth=0.9, label="the clock read alone: 27.8 ns")
    ax.set_xticks(range(len(CASES)))
    ax.set_xticklabels([c[1] for c in CASES])
    ax.set_ylabel("ns per event (real time)")
    ax.set_ylim(0, 235)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", fontsize=d2d.FONT_PT - 1.1, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
