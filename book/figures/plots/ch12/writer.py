# SPDX-License-Identifier: MIT
"""Figure for Chapter 12: list-mode writer throughput per fsync policy on the
book's VM (measurements/ch12/writer.txt), for short runs (320 MB, absorbed by
the page cache) and long runs (3.2 GB, more than the kernel lets stay dirty),
against the sorter's output at its own limit.

    python3 book/tools/figures.py build book/figures/plots/ch12/writer.py screen 2 pdf
"""
import os
import re
import sys

import matplotlib.pyplot as plt

import d2d

SRC = os.path.join(os.path.dirname(__file__), "../../../../measurements/ch12/writer.txt")
SORTER_LIMIT = 2.7  # M coincidences per second: 70 M singles/s x 0.039 (bm_sorter, Chapter 10)
LINE = re.compile(r"-> (short|long) fsync=(\w+) every=(\d+) buffers=(\d+): median ([\d.]+) M/s")
SHORT, LONG = d2d.tint(d2d.CAT[4], 0.5), d2d.CAT[4]


def read():
    out = {}
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            m = LINE.search(line)
            if m:
                run, policy, every, buffers, rate = m.groups()
                label = {"none": "none", "close": "close"}.get(policy, f"interval\n{every}")
                if buffers != "64":
                    label += "\n4 buffers"
                out.setdefault(label, {})[run] = float(rate)
    return out


def main(dst):
    data = read()
    labels = list(data)
    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    w = 0.38
    for i, label in enumerate(labels):
        for run, dx, color in (("short", -w / 2, SHORT), ("long", w / 2, LONG)):
            if run in data[label]:
                v = data[label][run]
                ax.bar(i + dx, v, w, color=color, label=f"{run} runs" if i == 0 else None)
                ax.text(i + dx, v + 0.5, f"{v:.2f}", ha="center")
    ax.axhline(SORTER_LIMIT, color=d2d.CAT[3], linewidth=0.9, label="sorter at its limit, 2.7 M/s")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("M coincidences per second")
    ax.set_xlabel("fsync policy (interval: blocks between fsyncs)")
    ax.tick_params(axis="y", labelsize=6.5)
    ax.set_ylim(0, 46)
    ax.legend(frameon=False, loc="upper center", ncol=3)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    d2d.save(fig, dst)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ch12-writer.png")
