# SPDX-License-Identifier: MIT
"""Figure for Chapter 39: the share of a point source's image within 8 mm of the source, without
and with time of flight, against the clock offset of block 29 alone and of a quarter of the
scanner, from measurements/ch39/tof.txt.

    python3 book/tools/figures.py build book/figures/plots/ch39/clock.py screen 10 pdf measurements/ch39/tof.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch39/tof.txt"
HEAD = re.compile(r"^The clock of (.+) \((\d+) blocks?\) off:")
ROW = re.compile(r"^\| (\d+) \| ([\d.]+)% \| ([\d.]+)% \|")


def tables(text):
    """[(name, blocks, [(offset, share without, share with), ...]), ...] from section 3."""
    out = []
    for line in text.splitlines():
        if (m := HEAD.match(line)) is not None:
            out.append((m.group(1), int(m.group(2)), []))
        elif out and (m := ROW.match(line)) is not None:
            out[-1][2].append((int(m.group(1)), float(m.group(2)), float(m.group(3))))
    return out


def main(dst):
    data = tables(SRC.read_text())
    fig, ax = d2d.figure(height=2.3, width=0.8)
    for k, (name, blocks, rows) in enumerate(data):
        off = [r[0] for r in rows]
        dash = d2d.DASHES[k]
        ax.plot(off, [r[1] for r in rows], color=d2d.MUTED, linestyle=dash, marker=d2d.MARKERS[k],
                markersize=3.2, linewidth=d2d.LINE_PT)
        ax.plot(off, [r[2] for r in rows], color=d2d.PART, linestyle=dash, marker=d2d.MARKERS[k],
                markersize=3.2, linewidth=d2d.LINE_PT)
        what = f"{name} ({blocks} block{'s' if blocks > 1 else ''})"
        d2d.label(ax, off[-1] + 20, rows[-1][2], f"TOF, {what}", c=d2d.PART, va="center",
                  ha="left")
    d2d.label(ax, 20, 101.0, "without TOF, either case", c=d2d.MUTED, va="bottom", ha="left")
    ax.set_xlim(-20, 1350)
    ax.set_ylim(None, 103)
    ax.set_xlabel("clock offset (ps)")
    ax.set_ylabel("image within 8 mm of the source (%)")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
