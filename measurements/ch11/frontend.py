#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 11: what each part of the front-end model costs in NECR.

At 30 and 100 MBq of the NEMA-style source, with the count-rate harness's
sorter, compare no dead time, a 1 us non-paralyzable dead time per crystal and
per block, each without and with pile-up.

    python3 measurements/ch11/frontend.py build/release/minidaq/apps > measurements/ch11/frontend.txt

Pile-up here adds the whole energy of a lost event to the event being
recorded, the worst case: a real pulse adds only the part of its light that
falls inside the integration window.
"""
import re
import subprocess
import sys

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
SORTER = ["--ehigh", "585", "--sectors", "1", "--fov", "120"]
DT = ["--deadtime", "non_paralyzable", "--tau", "1000"]
VARIANTS = [
    ("no dead time", []),
    ("per crystal", DT + ["--deadtime-unit", "crystal", "--pileup", "0"]),
    ("per crystal, pile-up", DT + ["--deadtime-unit", "crystal", "--pileup", "1"]),
    ("per block", DT + ["--deadtime-unit", "block", "--pileup", "0"]),
    ("per block, pile-up", DT + ["--deadtime-unit", "block", "--pileup", "1"]),
]
DECAYS = 1.5e7


def run(activity_bq, extra):
    out = subprocess.run([f"{APPS}/minidaq_sim", "--nema", "1", "--activity", str(activity_bq), "--seconds",
                          str(DECAYS / activity_bq), "--seed", "11", *SORTER, *extra],
                         capture_output=True, text=True, check=True).stdout
    r = {k: float(v) for k, v in (kv.split("=") for kv in re.search(r"^countrate (.*)$", out, re.M).group(1).split())}
    lost = re.search(r"^dead time .*: (\d+) lost \(([\d.]+)%\)", out, re.M)
    r["lost_pct"] = float(lost.group(2)) if lost else 0.0
    return r


def main():
    print(__doc__.split("\n\n")[0])
    print("1 us non-paralyzable dead time; rates per second by truth; NECR = T^2 / (T + S + kR).")
    print()
    for a in (30, 100):
        print(f"== {a} MBq")
        print(f"{'front end':<22} {'lost %':>6} {'trues/s':>9} {'scat/s':>9} {'rand/s':>9} {'SF':>6} {'NECR k=1':>9}")
        for label, extra in VARIANTS:
            r = run(a * 1e6, extra)
            print(f"{label:<22} {r['lost_pct']:>6.1f} {r['trues']:>9.0f} {r['scatters']:>9.0f} {r['randoms']:>9.0f} "
                  f"{r['sf']:>6.3f} {r['necr1']:>9.0f}")
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
