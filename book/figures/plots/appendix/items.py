# SPDX-License-Identifier: MIT
"""Figure for Appendix A: MiniDAQ's software items, grouped by the process they run in, and the
hazards each can contribute to, from docs/architecture/software-items.json.

    python3 book/tools/figures.py build book/figures/plots/appendix/items.py screen A pdf docs/architecture/software-items.json
"""
import json
import pathlib
import sys

import d2d
from matplotlib.patches import Rectangle

SRC = pathlib.Path(__file__).resolve().parents[4] / "docs/architecture/software-items.json"
SHORT = {"HZ-1": "coincidences\nlost or altered", "HZ-2": "acquisition\nstops", "HZ-3": "wrong or\nunknown settings",
         "HZ-4": "unauthorized\ncontrol", "HZ-5": "image filed\nwrongly"}


def main(dst):
    d = json.loads(SRC.read_text())
    hz = [h["id"] for h in d["hazards"]]
    items = [i for i in d["items"] if i["shipped"]]
    procs = list(dict.fromkeys(i["runs_in"] for i in items))
    fig, ax = d2d.figure(height=2.9, width=1.0)
    x = 0.0
    gap = 1.8
    for p in procs:
        group = [i for i in items if i["runs_in"] == p]
        for k, it in enumerate(group):
            for j, h in enumerate(hz):
                on = h in it["hazards"]
                ax.add_patch(Rectangle((x + k + 0.08, len(hz) - 1 - j + 0.08), 0.84, 0.84, lw=0,
                                       color=d2d.CAT[j % len(d2d.CAT)] if on else d2d.tint(d2d.MUTED, 0.12)))
            ax.text(x + k + 0.5, -0.15, it["id"], rotation=60, ha="right", va="top", fontsize=d2d.FONT_PT - 1.4,
                    color=d2d.INK, rotation_mode="anchor")
        ax.plot([x + 0.05, x + len(group) - 0.05], [len(hz) + 0.25] * 2, color=d2d.PART, lw=1.2)
        ax.text(x + len(group) / 2, len(hz) + 0.4, p if len(group) > 2 else p.replace("_", "_\n"), ha="center", va="bottom", fontsize=d2d.FONT_PT - 1.0,
                color=d2d.PART, family="monospace")
        x += len(group) + gap
    for j, h in enumerate(hz):
        ax.text(x - gap + 0.3, len(hz) - 1 - j + 0.5, f"{h}  " + SHORT.get(h, "").replace("\n", " "), va="center",
                fontsize=d2d.FONT_PT - 1.2, color=d2d.CAT[j % len(d2d.CAT)])
    ax.set_xlim(-0.1, x - gap + 6.5)
    ax.set_ylim(-2.4, len(hz) + 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
