# SPDX-License-Identifier: MIT
"""Figure for Chapter 34: the codebase survey as a treemap. Each software item's area is its code
lines, its color the commits that changed it since 2026-10-01, from measurements/ch34/survey.json.

    python3 book/tools/figures.py build book/figures/plots/ch34/treemap.py screen 8 pdf measurements/ch34/survey.json
"""
import json
import pathlib
import sys

import matplotlib.colors as mc
import matplotlib.patches as mp

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch34/survey.json"


def squarify(values, x, y, w, h):
    """Rectangles (x, y, w, h) for values sorted descending, by the squarified algorithm (Bruls,
    Huizing and van Wijk, 2000): each row is extended while its worst aspect ratio improves."""
    scale = w * h / sum(values)
    areas = [v * scale for v in values]
    out = []

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), s * s / (side * side * r)) for r in row)

    while areas:
        side = min(w, h)
        row = [areas[0]]
        while len(row) < len(areas) and worst(row + [areas[len(row)]], side) <= worst(row, side):
            row.append(areas[len(row)])
        s = sum(row)
        if w >= h:
            rw = s / h
            cy = y
            for r in row:
                out.append((x, cy, rw, r / rw))
                cy += r / rw
            x, w = x + rw, w - rw
        else:
            rh = s / w
            cx = x
            for r in row:
                out.append((cx, y, r / rh, rh))
                cx += r / rh
            y, h = y + rh, h - rh
        areas = areas[len(row):]
    return out


def main(dst):
    items = sorted(json.loads(SRC.read_text())["items"], key=lambda i: -i["code_lines"])
    rects = squarify([i["code_lines"] for i in items], 0, 0, 1.6, 1.0)
    cmap = mc.LinearSegmentedColormap.from_list("d2d", [d2d.tint(d2d.PART, 0.15), d2d.PART, d2d.CAT[3]])
    top = max(i["commits"] for i in items)
    fig, ax = d2d.figure(height=2.7, width=1.0)
    for it, (x, y, w, h) in zip(items, rects):
        c = cmap(it["commits"] / top)
        ax.add_patch(mp.Rectangle((x, y), w, h, facecolor=c, edgecolor="white", lw=1.2))
        if w * h > 0.012:
            dark = it["commits"] / top > 0.45
            ax.text(x + w / 2, y + h / 2, f"{it['item']}\n{it['code_lines']:,} lines\n{it['commits']} commits", ha="center",
                    va="center", fontsize=d2d.FONT_PT - (1.4 if w * h > 0.04 else 2.2), color="white" if dark else d2d.INK)
    ax.set_xlim(0, 1.6)
    ax.set_ylim(0, 1)
    ax.axis("off")
    sm = __import__("matplotlib.cm").cm.ScalarMappable(cmap=cmap, norm=mc.Normalize(0, top))
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("commits since 2026-10-01", fontsize=d2d.FONT_PT - 1)
    cb.ax.tick_params(labelsize=d2d.FONT_PT - 1.5)
    fig.tight_layout(pad=0.2)
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
