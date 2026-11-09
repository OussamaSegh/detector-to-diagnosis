# SPDX-License-Identifier: MIT
"""Figure for Chapter 27: the profile of the patient-like scan through the corrections, step by
step, against the truth, from section 4 of measurements/ch27/corrections.txt. A correct correction
is flat under the source (|s| < 80 mm).

    python3 book/tools/figures.py build book/figures/plots/ch27/profile.py screen 6 pdf measurements/ch27/corrections.txt
"""
import pathlib
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch27/corrections.txt"


def main(dst):
    text = SRC.read_text().split("## 4.")[1].split("## 5.")[0]
    rows = [l for l in text.splitlines() if l.startswith("| ")]
    head = [c.strip() for c in rows[0].split("|")[1:-1]]
    s = [int(h.split("=")[1]) for h in head[1:-1]]
    keep = [i for i, v in enumerate(s) if v <= 75]
    data = []
    for line in rows[1:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        data.append((cells[0], [float(cells[1 + i]) for i in keep], cells[-1]))
    fig, ax = d2d.figure(height=2.2, width=0.85)
    xs = [s[i] for i in keep]
    colors = [d2d.MUTED, d2d.CAT[1], d2d.CAT[0], d2d.CAT[3], d2d.PART]
    for k, (name, vals, rms) in enumerate(data[:5]):
        ax.plot(xs, vals, color=colors[k], marker=d2d.MARKERS[k], ms=3.5, ls=d2d.DASHES[k],
                lw=d2d.LINE_PT * (1.6 if k == 4 else 1), label=f"{name} (rms {rms})")
    truth = data[5]
    ax.plot(xs, truth[1], color=d2d.INK, lw=0.9, ls=":", label=f"{truth[0]} (rms {truth[2]})")
    ax.axhline(1, color=d2d.INK, lw=0.5)
    ax.set_xlabel("s, mm from the centre (the source's edge is at 80 mm)")
    ax.set_ylabel("profile / chord, mean 1")
    ax.set_ylim(0.6, 1.95)
    ax.legend(loc="upper left", fontsize=d2d.FONT_PT - 1.3, frameon=False, ncol=1)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
