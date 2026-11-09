#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 8's energy spectrum (book Figure "fig-ch08-spectrum"), as a table: singles per
10 keV bin from 0.2 s of simulated singles (5 MBq cylinder in water, seed 1), split by
whether the photon scattered in the phantom.

    python3 measurements/ch08/spectrum.py build/release/minidaq/apps/minidaq_sim > measurements/ch08/spectrum.txt
"""
import csv
import os
import subprocess
import sys
import tempfile


def main(sim):
    with tempfile.TemporaryDirectory() as tmp:
        csvp = os.path.join(tmp, "singles.csv")
        subprocess.run([sim, "--activity", "5e6", "--seconds", "0.2", "--seed", "1", "--truth", csvp],
                       check=True, stdout=subprocess.DEVNULL)
        direct, scattered = [0] * 80, [0] * 80
        with open(csvp, newline="") as f:
            for row in csv.DictReader(f):
                b = int(float(row["energy_kev"]) // 10)
                if 0 <= b < 80:
                    (scattered if row["scattered"] == "1" else direct)[b] += 1
    print("# minidaq_sim --activity 5e6 --seconds 0.2 --seed 1: singles per 10 keV bin")
    print("# bin_low_kev not_scattered scattered_in_phantom")
    for i in range(80):
        print(f"{i * 10} {direct[i]} {scattered[i]}")


if __name__ == "__main__":
    main(sys.argv[1])
