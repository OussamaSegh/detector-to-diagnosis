#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 8's table "Measured with MiniDAQ's simulator": coincidences per second by truth,
5 MBq uniform cylinder in water, 1 s, 4 ns window, for two energy windows. minidaq_sim's
default seed makes the run reproducible, so the table is exactly the same on every machine.

    python3 measurements/ch08/rates.py build/release/minidaq/apps/minidaq_sim > measurements/ch08/rates.txt
"""
import re
import subprocess
import sys

WINDOWS = ((100, 1000), (435, 650))


def run(sim, elow, ehigh):
    cmd = [sim, "--activity", "5e6", "--seconds", "1", "--elow", str(elow), "--ehigh", str(ehigh)]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    block = out[out.index("window "):out.index("sorter:")]
    rate = {k: int(re.search(rf"^\s+{k}\s+\d+\s+(\d+) /s", block, re.M).group(1))
            for k in ("trues", "scatters", "randoms", "multiples")}
    rate["sf"] = rate["scatters"] / (rate["trues"] + rate["scatters"])
    return " ".join(cmd[1:]), rate


def main(sim):
    print("# minidaq_sim, 5 MBq cylinder (r 80 mm, l 100 mm) in water (r 90 mm, l 180 mm), 1 s,")
    print("# 4 ns window, default seed; coincidences per second by truth")
    print("# elow_kev ehigh_kev trues scatters randoms multiples scatter_fraction")
    for elow, ehigh in WINDOWS:
        cmd, r = run(sim, elow, ehigh)
        print(f"{elow} {ehigh} {r['trues']} {r['scatters']} {r['randoms']} {r['multiples']} {r['sf']:.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
