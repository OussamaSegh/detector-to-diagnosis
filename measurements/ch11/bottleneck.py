#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 11: which MiniDAQ stage saturates first as the activity rises.

For each activity, record up to 4 M decays (at most 50 ms) of the NEMA-style
source with minidaq_sim (no dead time, so the singles rate grows linearly with
the activity), then replay the recording through the pipeline in real time
with minidaq_latency for 3 s (twice) and report how busy each stage was, what
the source dropped, and the end-to-end latency.

    python3 measurements/ch11/bottleneck.py build/release/minidaq/apps > measurements/ch11/bottleneck.txt

The pipeline runs its default sorter (4 ns fixed window, 435 to 585 keV, kill
all, delayed window at 100 ns) and a sink that discards the coincidences, so
the disk is not part of this measurement. Run nothing else on the machine.
"""
import os
import re
import subprocess
import sys
import tempfile

APPS = sys.argv[1] if len(sys.argv) > 1 else "build/release/minidaq/apps"
ACTIVITIES_MBQ = [20, 50, 100, 200, 300, 400]
REPEATS = 2
STAGES = ["source", "decode", "sort", "pair", "write"]


def record(activity_mbq, path):
    seconds = min(0.05, 4e6 / (activity_mbq * 1e6))
    subprocess.run([f"{APPS}/minidaq_sim", "--nema", "1", "--activity", str(activity_mbq * 1e6), "--seconds",
                    str(seconds), "--seed", "3", "--words", path], capture_output=True, check=True)


def replay(path):
    out = subprocess.run([f"{APPS}/minidaq_latency", "--words", path, "--speed", "1", "--seconds", "3"],
                         capture_output=True, text=True, check=True).stdout
    head = re.search(r"^rate ([\d.e+]+) words/s.*delivered (\d+), dropped (\d+)", out, re.MULTILINE)
    r = {"rate": float(head.group(1)), "delivered": int(head.group(2)), "dropped": int(head.group(3))}
    r["e2e_p99_us"] = float(re.search(r"^end-to-end\s+\d+\s+[\d.]+\s+([\d.]+)", out, re.MULTILINE).group(1))
    for s in STAGES:
        m = re.search(rf"^{s}\s+\d+\s+([\d.]+)\s+\d+\s+\d+\s+\d+$", out, re.MULTILINE)
        r[s] = float(m.group(1))
    return r


def main():
    print(__doc__.split("\n\n")[0])
    print("busy %: sum of a stage's batch service times over the wall time. The source's figure is the")
    print("time spent inside the replay source (clock reads and copies), not a limit of the pipeline.")
    print()
    print(f"{'MBq':>4} {'singles/s':>10} {'dropped %':>9} " + " ".join(f"{s:>7}" for s in STAGES) +
          f" {'e2e p99 us':>10}")
    with tempfile.TemporaryDirectory() as d:
        for a in ACTIVITIES_MBQ:
            path = os.path.join(d, f"nema-{a}.bin")
            record(a, path)
            for _ in range(REPEATS):
                r = replay(path)
                offered = r["delivered"] + r["dropped"]
                print(f"{a:>4} {r['rate']:>10.3g} {100.0 * r['dropped'] / offered:>9.2f} " +
                      " ".join(f"{r[s]:>7.1f}" for s in STAGES) + f" {r['e2e_p99_us']:>10.0f}")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
