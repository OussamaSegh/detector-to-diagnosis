#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 10 validation: the coincidence sorter against the simulator's truth.

For each activity and multiples policy, run minidaq_sim (which simulates, sorts,
and classifies every prompt by truth) and tabulate trues, scatters, randoms,
the delayed-window estimate and its error. The same seed at each activity
gives every policy the same singles.

    python3 measurements/ch10/validation.py build/release/minidaq/apps > measurements/ch10/validation.txt
"""
import re
import subprocess
import sys

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
# Activity (Bq) and simulated seconds: shorter at high activity, where randoms
# grow as the square of the activity.
RUNS = [(1e6, 1.0), (5e6, 0.4), (10e6, 0.2), (20e6, 0.1), (40e6, 0.05)]
POLICIES = ["kill_all", "take_all_goods", "take_winner_of_goods", "keep_if_only_one_good"]
FIELDS = {
    "prompts": r"^  prompts\s+(\d+)",
    "trues": r"^    trues\s+(\d+)",
    "scatters": r"^    scatter\s+(\d+)",
    "randoms": r"^    randoms\s+(\d+)",
    "from_multiples": r"^    from multiples\s+(\d+)",
    "delayed": r"^  delayed\s+(\d+)",
    "multiple_windows": r"^  multiple windows (\d+)",
    "singles": r"^window \d+ ps, energy .*: (\d+) singles",
}


def run(activity, seconds, policy, extra):
    out = subprocess.run([f"{APPS}/minidaq_sim", "--activity", str(activity), "--seconds", str(seconds),
                          "--ehigh", "585", "--seed", "21", "--policy", policy, *extra],
                         capture_output=True, text=True, check=True).stdout
    r = {}
    for key, pattern in FIELDS.items():
        m = re.search(pattern, out, re.MULTILINE)
        r[key] = int(m.group(1))
    return r


def table(title, extra):
    print(f"== {title}")
    print(f"{'MBq':>4} {'policy':<22} {'singles/s':>10} {'trues/s':>8} {'scat/s':>7} {'rand/s':>7} "
          f"{'delay/s':>7} {'err %':>11} {'R/P %':>6} {'mult/s':>7}")
    for activity, seconds in RUNS:
        for policy in POLICIES:
            r = run(activity, seconds, policy, extra)
            err = 100.0 * (r["delayed"] - r["randoms"]) / r["randoms"]
            # One standard deviation of err, treating both counts as independent Poisson.
            sigma = 100.0 * (r["delayed"] + r["randoms"]) ** 0.5 / r["randoms"]
            print(f"{activity / 1e6:>4.0f} {policy:<22} {r['singles'] / seconds:>10.0f} {r['trues'] / seconds:>8.0f} "
                  f"{r['scatters'] / seconds:>7.0f} {r['randoms'] / seconds:>7.0f} {r['delayed'] / seconds:>7.0f} "
                  f"{err:>+5.1f} ±{sigma:>4.1f} {100.0 * r['randoms'] / r['prompts']:>6.1f} "
                  f"{r['multiple_windows'] / seconds:>7.0f}")
            sys.stdout.flush()
    print()


def main():
    print("Sorter: 4 ns fixed window, 435-585 keV, delayed window at 100 ns.")
    print("singles/s: inside the energy window. err %: (delayed - true randoms) / true randoms, with one")
    print("standard deviation from counting statistics (both counts treated as independent Poisson,")
    print("which they are only roughly: they come from the same singles). R/P: randoms in the prompts.")
    print("mult/s: windows with three or more singles.")
    print("Seed 21; 90 mm water phantom, 80 mm source; the same singles for every policy at an activity.")
    print()
    table("no geometry cut", ["--sectors", "0"])
    table("sectors at least 1 apart, 120 mm field of view", ["--sectors", "1", "--fov", "120"])


if __name__ == "__main__":
    main()
