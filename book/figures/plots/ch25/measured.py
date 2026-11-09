# SPDX-License-Identifier: MIT
"""Figure for Chapter 25: the measured cost of the updater's commands and the exposure score of
the service unit with and without its hardening, from measurements/ch25/service_and_update.txt.

    python3 book/tools/figures.py build book/figures/plots/ch25/measured.py screen 5 pdf measurements/ch25/service_and_update.txt
"""
import pathlib
import re
import sys

import d2d

SRC = pathlib.Path(__file__).resolve().parents[4] / "measurements/ch25/service_and_update.txt"
CMD = re.compile(r"^\| ((?:install|rollback|confirm)[^|]*?) \| (\d+) \| (\d+) \|")
EXP = re.compile(r"^\| (without hardening|as shipped) \| ([\d.]+) \| (\w+) \|")


def main(dst):
    lines = SRC.read_text().splitlines()
    cmds = [(m.group(1), int(m.group(2)), int(m.group(3))) for m in map(CMD.match, lines) if m]
    exps = [(m.group(1), float(m.group(2)), m.group(3)) for m in map(EXP.match, lines) if m]
    fig, (ax, bx) = d2d.figure(height=2.0, width=1.0, ncols=2, gridspec_kw={"width_ratios": [1.6, 1]})
    y = list(range(len(cmds)))[::-1]
    for yi, (name, ms, code) in zip(y, cmds):
        c = d2d.PART if name.startswith("install") else (d2d.CAT[0] if name.startswith("rollback") else d2d.CAT[2])
        ax.barh(yi, ms, color=c if code == 0 else d2d.tint(c, 0.4), height=0.6)
        ax.text(ms + 1.5, yi, f"{ms} ms" + ("" if code == 0 else f", exit {code}"), va="center",
                fontsize=d2d.FONT_PT - 1, color=d2d.INK)
    ax.set_yticks(y)
    ax.set_yticklabels([c[0] for c in cmds])
    ax.set_xlim(0, 80)
    ax.set_xlabel("ms, one run each")
    ax.grid(axis="y", visible=False)
    ax.set_title("updater commands", fontsize=d2d.FONT_PT, color=d2d.INK)
    for i, (name, score, rating) in enumerate(exps):
        c = d2d.MUTED if score > 5 else d2d.CAT[2]
        bx.bar(i, score, color=c, width=0.6)
        bx.text(i, score + 0.25, f"{score} {rating}", ha="center", fontsize=d2d.FONT_PT - 1, color=d2d.INK)
    bx.set_xticks(range(len(exps)))
    bx.set_xticklabels([e[0].replace("without hardening", "no hardening") for e in exps])
    bx.set_ylim(0, 10.8)
    bx.set_ylabel("exposure, 0 to 10")
    bx.grid(axis="x", visible=False)
    bx.set_title("systemd-analyze security", fontsize=d2d.FONT_PT, color=d2d.INK)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
