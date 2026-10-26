#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 11 window study: how the time and energy windows change the NECR.

At two activities of the NEMA-style source (30 MBq, low on the count-rate curve,
and 100 MBq, near its peak), with the 1 us non-paralyzable block dead time and
pile-up of countrate.py, sweep the coincidence time window at a fixed 435 to
585 keV energy window, then the lower energy threshold at a fixed 4 ns time
window, and report trues, scatters, randoms, the scatter fraction and the NECR.

    python3 measurements/ch11/windows.py build/release/minidaq/apps > measurements/ch11/windows.txt

The simulated detector has a 300 ps FWHM coincidence time resolution and a
12% FWHM energy resolution at 511 keV; a real detector's numbers (assumption:
confirm with team for your scanner) move the optimum.
"""
import re
import subprocess
import sys

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
ACTIVITIES_MBQ = [30, 100]
WINDOWS_PS = [500, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
LOWER_KEV = [350, 400, 435, 460, 480]
FRONT_END = ["--deadtime", "non_paralyzable", "--tau", "1000", "--pileup", "1"]
SORTER = ["--ehigh", "585", "--sectors", "1", "--fov", "120"]
DECAYS = 1.5e7


def run(activity_bq, window_ps, elow_kev):
    seconds = DECAYS / activity_bq
    out = subprocess.run([f"{APPS}/minidaq_sim", "--nema", "1", "--activity", str(activity_bq), "--seconds",
                          str(seconds), "--seed", "11", "--window", str(window_ps), "--elow", str(elow_kev),
                          *SORTER, *FRONT_END], capture_output=True, text=True, check=True).stdout
    line = re.search(r"^countrate (.*)$", out, re.MULTILINE).group(1)
    r = {k: float(v) for k, v in (kv.split("=") for kv in line.split())}
    r["seconds"] = seconds
    return r


def row(label, r):
    t_n = round(r["trues"] * r["seconds"])
    return (f"{label:>8} {r['trues']:>9.0f} {r['scatters']:>9.0f} {r['randoms']:>9.0f} {t_n:>8} "
            f"{r['sf']:>6.3f} {r['necr1']:>9.0f} {r['necr2']:>9.0f}")


def header(first):
    return (f"{first:>8} {'trues/s':>9} {'scat/s':>9} {'rand/s':>9} {'T n':>8} {'SF':>6} "
            f"{'NECR k=1':>9} {'NECR k=2':>9}")


def main():
    print(__doc__.split("\n\n")[0])
    print("Rates per second by truth; NECR = T^2 / (T + S + kR). T n: trues counted (relative standard")
    print("deviation about 1/sqrt(T n)). All runs use the same seed, so neighboring rows share their decays.")
    print()
    for a in ACTIVITIES_MBQ:
        print(f"== {a} MBq, time window (energy 435 to 585 keV)")
        print(header("window"))
        for w in WINDOWS_PS:
            print(row(f"{w / 1000:g} ns", run(a * 1e6, w, 435)))
            sys.stdout.flush()
        print()
        print(f"== {a} MBq, lower energy threshold (window 4 ns, upper 585 keV)")
        print(header("lower"))
        for e in LOWER_KEV:
            print(row(f"{e} keV", run(a * 1e6, 4000, e)))
            sys.stdout.flush()
        print()


if __name__ == "__main__":
    main()
