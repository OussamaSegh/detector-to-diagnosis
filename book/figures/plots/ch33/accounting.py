# SPDX-License-Identifier: MIT
"""Figure for Chapter 33: every count between the stages of the phantom acquisition, from
measurements/ch33/e2e/e2e.json: the singles sent and what became of each, the pair windows, the
coincidences written and their sinogram bins. Each bar is one balance the end-to-end checks verify.

    python3 book/tools/figures.py build book/figures/plots/ch33/accounting.py screen 8 pdf measurements/ch33/e2e/e2e.json
"""
import json
import pathlib
import sys
import textwrap

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch33/e2e/e2e.json"


def main(dst):
    run = next(a for a in json.loads(SRC.read_text())["acquisitions"] if a["name"] == "phantom")
    s, k, so, sg = run["sent"], run["link"], run["sorter"], run["sinogram"]
    bars = [
        ("singles sent", [("delivered", k["words_delivered"]), ("lost", s["singles"] - k["words_delivered"])]),
        ("singles at the sorter", [("energy rejected", so["energy_rejected"]), ("alone", so["singles_alone"]),
                                   ("in pair windows", 2 * so["pair_windows"]), ("in multiples", so["singles_in_multiples"])]),
        ("pair windows", [("prompts", so["prompts"]), ("geometry rejected", so["geometry_rejected"])]),
        ("coincidences written", [("prompts", run["records"]["prompts"]), ("delayed", run["records"]["delayed"])]),
        ("sinogram", [("binned prompts", sg["prompts"]), ("binned delayeds", sg["delayeds"]), ("outside the FOV", sg["outside_fov"])]),
    ]
    colors = [d2d.PART, d2d.CAT[0], d2d.CAT[2], d2d.CAT[3], d2d.MUTED]
    fig, ax = d2d.figure(height=2.3, width=1.0)
    y = list(range(len(bars)))[::-1]
    for yi, (name, parts) in zip(y, bars):
        total = sum(v for _, v in parts)
        left = 0.0
        for j, (lab, v) in enumerate(parts):
            if v == 0:
                continue
            w = v / total
            ax.barh(yi, w, left=left, color=colors[j], height=0.62, edgecolor="white", lw=0.6)
            if w > 0.07:
                ax.text(left + w / 2, yi, f"{lab}\n{v:,}", ha="center", va="center", fontsize=d2d.FONT_PT - 1.6, color="white")
            left += w
        ax.text(1.01, yi, f"{total:,}", va="center", fontsize=d2d.FONT_PT - 1.1, color=d2d.INK)
    ax.set_yticks(y)
    ax.set_yticklabels([b[0] for b in bars])
    ax.set_xlim(0, 1.13)
    ax.set_xticks([])
    ax.grid(False)
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)
    small = "; ".join(f"{name}: {v:,} {lab}" for name, parts in bars for lab, v in parts
                      if 0 < v / sum(x for _, x in parts) <= 0.07)
    ax.set_xlabel(textwrap.fill("too small to label: " + small, 150), fontsize=d2d.FONT_PT - 1.5)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
