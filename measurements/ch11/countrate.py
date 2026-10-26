#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 11 count-rate harness: NEMA-style count-rate curves from the simulator.

For each front-end model and activity, run minidaq_sim with the NEMA-style line
source in a 203 mm phantom (--nema 1), sort with the default sorter (4 ns fixed
window, 435 to 585 keV, kill all, sectors at least 1 apart, 120 mm field of
view) and read the trues, scatters and randoms by truth, the scatter fraction
and the NECR (k = 1 and k = 2).

    python3 measurements/ch11/countrate.py build/release/minidaq/apps > measurements/ch11/countrate.txt

This is a NEMA-style test, not a NEMA NU 2 measurement: the scanner is
MiniDAQ's model ring, the phantom is water, and the rates come from the ground
truth rather than from the sinogram analysis the standard prescribes.
"""
import re
import subprocess
import sys

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
ACTIVITIES_MBQ = [5, 10, 20, 30, 50, 70, 100, 140, 200, 300, 400, 700, 1000]
# Front-end models: (label, extra minidaq_sim arguments). The 1 us block dead
# time is an assumption for illustration (confirm with team for your scanner).
MODELS = [
    ("no dead time", []),
    ("non-paralyzable 1 us per block, pile-up",
     ["--deadtime", "non_paralyzable", "--tau", "1000", "--pileup", "1"]),
    ("paralyzable 1 us per block, pile-up", ["--deadtime", "paralyzable", "--tau", "1000", "--pileup", "1"]),
]
SORTER = ["--ehigh", "585", "--sectors", "1", "--fov", "120"]
DECAYS = 1.5e7  # per point: about 20 s of simulation each on the book's VM


def seconds_for(activity_bq):
    return min(2.0, max(0.004, DECAYS / activity_bq))


def run(activity_bq, extra):
    seconds = seconds_for(activity_bq)
    out = subprocess.run([f"{APPS}/minidaq_sim", "--nema", "1", "--activity", str(activity_bq), "--seconds",
                          str(seconds), "--seed", "11", *SORTER, *extra],
                         capture_output=True, text=True, check=True).stdout
    line = re.search(r"^countrate (.*)$", out, re.MULTILINE).group(1)
    r = {k: float(v) for k, v in (kv.split("=") for kv in line.split())}
    lost = re.search(r"^dead time .*: (\d+) lost \(([\d.]+)%\)", out, re.MULTILINE)
    r["lost_pct"] = float(lost.group(2)) if lost else 0.0
    r["seconds"] = seconds
    return r


def main():
    print(__doc__.split("\n\n")[0])
    print("Rates per second by truth; NECR = T^2 / (T + S + kR). seconds: simulated time per point.")
    print("lost %: singles lost to dead time (including those piled up). T n: trues counted, so the relative")
    print("standard deviation of the trues is about 1/sqrt(T n); SF is left out below 100 counted T + S.")
    print()
    for label, extra in MODELS:
        print(f"== {label}")
        print(f"{'MBq':>5} {'seconds':>7} {'singles/s':>10} {'lost %':>6} {'trues/s':>9} {'scat/s':>9} "
              f"{'rand/s':>9} {'T n':>7} {'SF':>6} {'NECR k=1':>9} {'NECR k=2':>9}")
        for a in ACTIVITIES_MBQ:
            r = run(a * 1e6, extra)
            t_n = round(r["trues"] * r["seconds"])
            ts_n = round((r["trues"] + r["scatters"]) * r["seconds"])
            sf = f"{r['sf']:>6.3f}" if ts_n >= 100 else f"{'-':>6}"
            print(f"{a:>5} {r['seconds']:>7.3f} {r['singles']:>10.4g} {r['lost_pct']:>6.1f} {r['trues']:>9.0f} "
                  f"{r['scatters']:>9.0f} {r['randoms']:>9.0f} {t_n:>7} {sf} {r['necr1']:>9.0f} {r['necr2']:>9.0f}")
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
