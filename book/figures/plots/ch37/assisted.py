# SPDX-License-Identifier: MIT
"""Figure for Chapter 37: the commits an assistant helped make, those that changed product code,
and those of them that changed no test, from section 1 of measurements/ch37/provenance.txt; the
nine were read one by one, and the text classifies them.

    python3 book/tools/figures.py build book/figures/plots/ch37/assisted.py screen 9 pdf measurements/ch37/provenance.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch37/provenance.txt"
# The nine commits of product code without a test, as read one by one (Chapter 37's text and
# measurements/ch37/README.md): what kind of change each is.
READ = [("comment, assertion\nand warning fixes", 6), ("optimization", 1), ("behavior, caught by\nsystem.platform", 1),
        ("robustness, no\ntest named", 1)]


def main(dst):
    t = SRC.read_text()
    total = int(re.search(r"commits (\d+), merges", t).group(1))
    merges = int(re.search(r"merges (\d+)", t).group(1))
    named = int(re.search(r"named in (\d+) of", t).group(1))
    product = int(re.search(r"change product code: (\d+)", t).group(1))
    notest = int(re.search(r"without a test changed in the same commit: (\d+)", t).group(1))
    assert notest == sum(n for _, n in READ)
    stages = [(f"commits ({merges} merges left out)", total - merges), ("name an assistant", named),
              ("change product code", product), ("change no test", notest)]
    fig, (ax, bx) = d2d.figure(height=1.8, width=1.0, ncols=2, gridspec_kw={"width_ratios": [1.3, 1]})
    for k, (n, v) in enumerate(stages):
        y = len(stages) - 1 - k
        ax.barh(y, v, color=d2d.PART if k == len(stages) - 1 else d2d.tint(d2d.CAT[0], 1.0 - 0.22 * k), height=0.66)
        ax.text(v + 4, y, str(v), va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels([n for n, _ in reversed(stages)])
    ax.set_xlim(0, stages[0][1] * 1.15)
    ax.set_xlabel("commits")
    ax.grid(axis="y", visible=False)
    for k, (n, v) in enumerate(reversed(READ)):
        bx.barh(k, v, color=d2d.PART if k == len(READ) - 1 else d2d.CAT[1], height=0.66)
        bx.text(v + 0.15, k, str(v), va="center", fontsize=d2d.FONT_PT - 1.2, color=d2d.INK)
    bx.set_yticks(range(len(READ)))
    bx.set_yticklabels([n for n, _ in reversed(READ)], fontsize=d2d.FONT_PT - 1.2)
    bx.set_xlim(0, 7.5)
    bx.set_title(f"the {notest}, read one by one", fontsize=d2d.FONT_PT, color=d2d.INK)
    bx.grid(axis="y", visible=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
