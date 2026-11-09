# SPDX-License-Identifier: MIT
"""Figure for Chapter 33: the acceptance specification's verdicts at each release candidate, from
the acceptance records of 0.7.0 (measurements/ch33) and of 0.8.0, 0.9.0 and 1.0.0
(measurements/release-*/acceptance.md).

    python3 book/tools/figures.py build book/figures/plots/ch33/acceptance.py screen 8 pdf "measurements/ch33/acceptance-0.7.0.md measurements/release-0.8.0/acceptance.md measurements/release-0.9.0/acceptance.md measurements/release-1.0.0/acceptance.md"
"""
import pathlib
import sys

import matplotlib.patches as mp

import d2d

ROOT = pathlib.Path(__file__).resolve().parents[4]
FILES = [("0.7.0", "measurements/ch33/acceptance-0.7.0.md"), ("0.8.0", "measurements/release-0.8.0/acceptance.md"),
         ("0.9.0", "measurements/release-0.9.0/acceptance.md"), ("1.0.0", "measurements/release-1.0.0/acceptance.md")]
SHORT = {"ACC-01": "pipeline throughput", "ACC-02": "writer throughput", "ACC-03": "30-minute soak",
         "ACC-04": "end-to-end latency", "ACC-05": "chain end to end", "ACC-06": "the image",
         "ACC-07": "system test plan", "ACC-08": "release checks", "ACC-09": "trace, risk, baseline"}


def main(dst):
    table = {}
    for v, p in FILES:
        for line in (ROOT / p).read_text().splitlines():
            if line.startswith("| ACC-"):
                cells = line.split("|")
                table[(cells[1].strip()[:6], v)] = cells[-2].strip()
    color = {"PASS": d2d.CAT[2], "FAIL": d2d.CAT[3], "MISSING": d2d.MUTED, "STALE": d2d.tint(d2d.MUTED, 0.5)}
    ids = sorted({k[0] for k in table})
    fig, ax = d2d.figure(height=2.5, width=0.75)
    for i, acc in enumerate(ids):
        for j, (v, _) in enumerate(FILES):
            verdict = table.get((acc, v), "")
            ax.add_patch(mp.FancyBboxPatch((j + 0.06, -i - 0.42), 0.88, 0.84, boxstyle="round,pad=0,rounding_size=0.08",
                                           color=color.get(verdict, "white"), lw=0))
            ax.text(j + 0.5, -i, verdict, ha="center", va="center", fontsize=d2d.FONT_PT - 1.6, color="white", fontweight="bold")
    ax.set_xlim(0, len(FILES))
    ax.set_ylim(-len(ids) + 0.4, 0.6)
    ax.set_xticks([j + 0.5 for j in range(len(FILES))])
    ax.set_xticklabels([v for v, _ in FILES])
    ax.xaxis.tick_top()
    ax.set_yticks([-i for i in range(len(ids))])
    ax.set_yticklabels([f"{a} {SHORT[a]}" for a in ids])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
