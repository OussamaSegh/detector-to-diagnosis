# SPDX-License-Identifier: MIT
"""Figure for Chapter 8: the energy spectrum of simulated singles, by truth.

    build/release/minidaq/apps/minidaq_sim --activity 5e6 --seconds 0.2 --truth singles.csv
    python3 book/tools/figures/ch08_energy_spectrum.py singles.csv book/src/img/ch08-spectrum.png
"""
import csv
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main(src, dst):
    direct, scattered = [], []
    with open(src, newline="") as f:
        for row in csv.DictReader(f):
            (scattered if row["scattered"] == "1" else direct).append(float(row["energy_kev"]))
    bins = [10 * i for i in range(0, 76)]
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=300)
    ax.hist([direct, scattered], bins=bins, stacked=True, color=["#1f5fa8", "#e08a2b"],
            label=["not scattered in the phantom", "scattered in the phantom"])
    for x in (435, 650):
        ax.axvline(x, color="black", linestyle="--", linewidth=0.8)
    ax.text(658, ax.get_ylim()[1] * 0.5, "energy window\n435 to 650 keV", fontsize=8)
    ax.set_xlabel("measured energy (keV)")
    ax.set_ylabel("singles per 10 keV")
    ax.set_xlim(0, 800)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
