# SPDX-License-Identifier: MIT
"""Figure for Chapter 29: the time of one forward projection and one backprojection, numpy against
the C++ projector on 1, 2 and 4 threads, for the first C++ version and the current one, from
section 2 of measurements/ch29/first-version.txt and measurements/ch29/projector.txt.

    python3 book/tools/figures.py build book/figures/plots/ch29/speed.py screen 6 pdf "measurements/ch29/projector.txt measurements/ch29/first-version.txt"
"""
import pathlib
import re
import sys

import d2d

DIR = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch29"
ROW = re.compile(r"^\| (numpy|C\+\+, \d threads?) \| ([\d.]+) ms \| ([\d.]+) ms \|")


def rows(name):
    text = (DIR / name).read_text().split("## 2.")[1].split("## 3.")[0]
    return [(m.group(1), float(m.group(2)), float(m.group(3))) for m in map(ROW.match, text.splitlines()) if m]


def main(dst):
    now, first = rows("projector.txt"), rows("first-version.txt")
    fig, axes = d2d.figure(height=1.9, width=1.0, ncols=2, sharey=True)
    for ax, k, title in zip(axes, (1, 2), ("forward projection", "backprojection")):
        for i, (a, b) in enumerate(zip(first, now)):
            ax.barh(i + 0.18, a[k], height=0.34, color=d2d.tint(d2d.MUTED, 0.45), label="first C++ version" if i == 1 else None)
            c = d2d.MUTED if b[0] == "numpy" else d2d.PART
            ax.barh(i - 0.18, b[k], height=0.34, color=c, label="current" if i == 1 else None)
            ax.text(b[k] + 1, i - 0.18, f"{b[k]:.0f}", va="center", fontsize=d2d.FONT_PT - 1.3, color=d2d.INK)
            if b[0] != "numpy":
                ax.text(a[k] + 1, i + 0.18, f"{a[k]:.0f}", va="center", fontsize=d2d.FONT_PT - 1.3, color=d2d.MUTED)
        ax.set_title(title, fontsize=d2d.FONT_PT, color=d2d.INK)
        ax.set_xlabel("ms, median of 7")
        ax.set_xlim(0, 80)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(now)))
    axes[0].set_yticklabels([r[0] for r in now])
    axes[0].invert_yaxis()
    axes[1].legend(loc="lower right", fontsize=d2d.FONT_PT - 1.2, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
