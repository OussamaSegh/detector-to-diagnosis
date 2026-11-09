# SPDX-License-Identifier: MIT
"""Draws a flame graph from a folded-stack file (measurements/ch05/flame/*.folded) in the
book's style: width is the share of samples, the root at the bottom, frames narrower than
0.3% left out, and the product's sort path highlighted. Used by flame_before.py and
flame_after.py."""
import os
import zlib

import matplotlib.patches as mpatches

import d2d

ROOT = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch05/flame")
HOT = ("mdq-sort", "time_order", "SortStage", "sort_batch", "std::__introsort", "std::sort")
MIN_SHARE = 0.003
MAX_DEPTH = 24


def read(name):
    tree = {}
    total = 0
    for line in open(os.path.join(ROOT, name), encoding="utf-8"):
        stack, _, n = line.rstrip().rpartition(" ")
        if not stack:
            continue
        n = int(n)
        total += n
        node = tree
        for f in stack.split(";")[:MAX_DEPTH]:
            e = node.setdefault(f, [0, {}])
            e[0] += n
            node = e[1]
    return tree, total


def short(f):
    f = f.replace("minidaq::", "").replace("(anonymous namespace)::", "")
    return f.split("(")[0] if "(" in f else f


def draw(name, dst, title):
    tree, total = read(name)
    fig, ax = d2d.figure(height=3.2)
    h = 1.0

    def walk(node, x0, depth):
        x = x0
        for f, (n, kids) in sorted(node.items()):
            w = n / total
            if w >= MIN_SHARE:
                hot = any(k in f for k in HOT)
                hue = zlib.crc32(f.encode()) % 1000 / 1000
                c = d2d.PART if hot else d2d.tint(d2d.CAT[1] if hue < 0.5 else d2d.CAT[3], 0.25 + 0.35 * hue)
                ax.add_patch(mpatches.Rectangle((x, depth * h), w, h * 0.92, facecolor=c, edgecolor="white",
                                                linewidth=0.3))
                label = short(f)
                chars = int(w * 260)
                if chars >= 4:
                    txt = label if len(label) <= chars else label[: max(chars - 1, 1)] + "…"
                    ax.text(x + 0.002, depth * h + 0.46, txt, va="center", fontsize=4.6,
                            color="white" if hot else d2d.INK, clip_on=True)
                walk(kids, x, depth + 1)
            x += w

    walk(tree, 0.0, 0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, MAX_DEPTH * h)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(f"share of samples ({title}); highlighted: the sort path")
    ax.set_yticks([])
    ax.grid(False)
    for s in ("left", "top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    d2d.save(fig, dst)
