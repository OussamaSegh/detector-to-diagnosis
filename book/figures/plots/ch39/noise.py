# SPDX-License-Identifier: MIT
"""Figure for Chapter 39: the background variability of the cylinder with its hot rod at each OSEM
iteration, without and with time of flight, at 300 and 500 ps, from measurements/ch39/tof.txt.

    python3 book/tools/figures.py build book/figures/plots/ch39/noise.py screen 10 pdf measurements/ch39/tof.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch39/tof.txt"
HEAD = re.compile(r"^At (\d+) ps: ")
ROW = re.compile(r"^\| (\d+) \| ([\d.]+) / ([\d.]+) \| [\d.]+% / [\d.]+% \| ([\d.]+)% / ([\d.]+)% \|")


def tables(text):
    """{ctr: [(iteration, cr without, cr with, bv without, bv with), ...]} from section 2."""
    out, ctr = {}, None
    for line in text.splitlines():
        if (m := HEAD.match(line)) is not None:
            ctr = int(m.group(1))
            out[ctr] = []
        elif ctr is not None and (m := ROW.match(line)) is not None:
            out[ctr].append(tuple(float(g) for g in m.groups()))
    return out


def main(dst):
    data = tables(SRC.read_text())
    fig, axes = d2d.figure(height=2.4, ncols=2, sharey=True)
    for ax, (ctr, rows) in zip(axes, sorted(data.items())):
        for k, (name, c, dash) in enumerate((("without TOF", d2d.MUTED, "--"),
                                             (f"TOF {ctr} ps", d2d.PART, "-"))):
            its = [r[0] for r in rows]
            bv = [r[3 + k] for r in rows]
            ax.plot(its, bv, color=c, linestyle=dash, marker=d2d.MARKERS[k], markersize=3.2,
                    linewidth=d2d.LINE_PT)
            d2d.label(ax, its[-1] + 0.4, bv[-1], name, c=c, va="center", ha="left")
        ax.set_xlim(0.5, 16.5)
        ax.set_xticks(range(1, 13))
        ax.set_xlabel("OSEM iteration (8 subsets)")
        ax.set_title(f"timing resolution {ctr} ps", fontsize=d2d.FONT_PT)
    axes[0].set_ylabel("background variability (%)")
    axes[0].set_ylim(0, None)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
