# SPDX-License-Identifier: MIT
"""Figure for Chapter 24: the board's FIFO (4,096 words, link 25,000 words/s) through a burst, from
the chapter's arithmetic: events at 50,000 words/s fill it in 164 ms; at 27,000 words/s in 2.05 s;
with the triggers off it drains in 164 ms.

    python3 book/tools/figures.py build book/figures/plots/ch24/fifo.py screen 5 pdf
"""
import sys

import d2d

DEPTH, OUT = 4096, 25_000


def level(rate_in, t_off, t_end, dt=0.0005):
    t, lvl, lost, ts, ls = 0.0, 0.0, 0.0, [], []
    while t <= t_end:
        inc = rate_in * dt if t < t_off else 0.0
        lvl += inc - OUT * dt
        if lvl > DEPTH:
            lost += lvl - DEPTH
            lvl = DEPTH
        lvl = max(lvl, 0.0)
        ts.append(t * 1000)
        ls.append(lvl)
        t += dt
    return ts, ls


def main(dst):
    fig, ax = d2d.figure(height=2.1, width=0.75)
    for k, (rin, label) in enumerate([(50_000, "events at 50,000 words/s"), (27_000, "events at 27,000 words/s")]):
        ts, ls = level(rin, 0.4, 0.75)
        ax.plot(ts, ls, color=d2d.PART if k == 0 else d2d.CAT[0], linestyle=d2d.DASHES[k], linewidth=d2d.LINE_PT, label=label)
    ax.axhline(DEPTH, color=d2d.SEM["mistakes"], linewidth=0.8, linestyle=":")
    ax.axvspan(164, 400, ymin=0, ymax=1, color=d2d.tint(d2d.SEM["mistakes"], 0.08), linewidth=0)
    ax.text(282, 4200, "full: every new event is lost and the flag set", ha="center", va="bottom", fontsize=d2d.FONT_PT - 1.1)
    ax.axvline(400, color=d2d.INK, linewidth=0.8)
    ax.text(405, 3000, "triggers off", fontsize=d2d.FONT_PT - 1, va="center")
    ax.annotate("drains in 164 ms:\nwhat a stop must wait", xy=(564, 0), xytext=(590, 1900), fontsize=d2d.FONT_PT - 1,
                arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.6})
    ax.annotate("fills in 164 ms", xy=(164, 4096), xytext=(40, 3300), fontsize=d2d.FONT_PT - 1,
                arrowprops={"arrowstyle": "->", "color": d2d.INK, "linewidth": 0.6})
    ax.set_xlim(0, 750)
    ax.set_ylim(0, 4900)
    ax.set_xlabel("ms after the triggers went on")
    ax.set_ylabel("FIFO level (words)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.82), fontsize=d2d.FONT_PT - 1, frameon=False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1])
