# SPDX-License-Identifier: MIT
"""Figure for Chapter 7: coverage against executions in the three fuzzing campaigns, from the
libFuzzer log summaries in measurements/ch07/fuzz.

    python3 book/tools/figures.py build book/figures/plots/ch07/fuzz.py screen 1 pdf measurements/ch07/fuzz
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch07/fuzz"
CAMPAIGNS = [("config.txt", "configuration, 30 min"), ("decoder.txt", "decoder, 60 min"), ("protocol.txt", "control protocol, 60 min")]
LINE = re.compile(r"^#(\d+)\s+(?:INITED|NEW|REDUCE|DONE|pulse)\s+cov: (\d+)")


def series(name):
    xs, ys = [], []
    for line in (SRC / name).read_text().splitlines():
        m = LINE.match(line)
        if m:
            xs.append(int(m.group(1)))
            ys.append(int(m.group(2)))
    return xs, ys


def main(dst):
    fig, axes = d2d.figure(height=1.9, width=1.0, ncols=3)
    for k, (ax, (name, title)) in enumerate(zip(axes, CAMPAIGNS)):
        xs, ys = series(name)
        ax.step(xs, ys, where="post", color=d2d.PART, linewidth=d2d.LINE_PT)
        ax.plot(xs[-1], ys[-1], marker="o", color=d2d.PART, markersize=3.5)
        ax.text(xs[-1], ys[-1], f"{ys[-1]:,}", ha="right", va="bottom", fontsize=d2d.FONT_PT - 0.8)
        ax.set_xscale("log")
        ax.set_xlim(3, xs[-1] * 2.5)
        ax.set_title(title, fontsize=d2d.FONT_PT, loc="left")
        ax.set_xlabel("executions")
        if k == 0:
            ax.set_ylabel("edges covered")
        if name == "decoder.txt":
            ax.annotate("flat after 7,755", xy=(7755, 101), xytext=(150, 86.5), fontsize=d2d.FONT_PT - 0.8,
                        arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.7})
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
