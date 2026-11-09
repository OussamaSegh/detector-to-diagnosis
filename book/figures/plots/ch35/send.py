# SPDX-License-Identifier: MIT
"""Figure for Chapter 35: sending a 47-slice series over loopback, the median of 5 sends and its
range, for each maximum PDU length, with the package's test archive and with pynetdicom, and once
without TCP_NODELAY, from section 5 of measurements/ch35/dicom.txt.

    python3 book/tools/figures.py build book/figures/plots/ch35/send.py screen 9 pdf measurements/ch35/dicom.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch35/dicom.txt"
ROW = re.compile(r"^\s+(test archive|pynetdicom)\s+max PDU\s+(\w+)(, sender WITHOUT TCP_NODELAY)?:\s+([\d.]+) ms \(([\d.]+) to ([\d.]+)\)")


def main(dst):
    rows = [m.groups() for m in map(ROW.match, SRC.read_text().splitlines()) if m]
    fig, ax = d2d.figure(height=2.1, width=0.9)
    labels = []
    for k, (who, pdu, nodelay, med, lo, hi) in enumerate(rows):
        med, lo, hi = float(med), float(lo), float(hi)
        c = d2d.MUTED if nodelay else (d2d.PART if who == "test archive" else d2d.CAT[0])
        ax.plot([lo, hi], [k, k], color=d2d.tint(c, 0.5), lw=3, solid_capstyle="round")
        ax.scatter(med, k, color=c, s=18, zorder=3)
        ax.text(hi * 1.12, k, f"{med:.0f} ms", va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
        labels.append(f"{who}, PDU {pdu}" + (", no TCP_NODELAY" if nodelay else ""))
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(40, 5000)
    ax.set_xlabel("ms to send 47 instances (1.6 MB), median and range of 5")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
