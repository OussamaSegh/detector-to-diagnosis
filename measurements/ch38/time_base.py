#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 38 measurements: what the time base monitor finds, what it raises on a healthy run, and
what it costs.

Each run goes the way of a real one: minidaq_send simulates the scanner (a cylinder source, 1.5 MBq
in the field of view, its own seed) and sends the singles over UDP in real time to minidaq_server,
whose pipeline sorts them and runs the monitor in the pair stage; intervals of 0.5 s, the
baseline of 2 intervals, the default limits (warning 100 ps, alarm 250 ps, 5 standard deviations).
A fault is a clock error that minidaq_send gives block 29: a step at 2.0 s of detector time, or a
drift from the start. The status after the run gives each block's latest offset, its largest, its
intervals at alarm and the time of the first.

Then the benchmark bm_timing_monitor: record() per coincidence and one fit of 72 offsets.

    python3 measurements/ch38/time_base.py build/release > measurements/ch38/time_base.txt

The argument is a build directory with minidaq/apps and benchmarks (a release build).
"""
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile

BUILD = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/release")
ROOT = pathlib.Path(__file__).resolve().parents[2]
os.environ.setdefault("MINIDAQ_APPS", str(BUILD / "minidaq" / "apps"))
sys.path.insert(0, str(ROOT / "minidaq" / "tests" / "system"))
from systest import Ctl, Server, app, eventually, write_json  # noqa: E402

UDP_PORT = re.compile(r"UDP readout on [\d.]+:(\d+)")
BLOCK = 29
ACTIVITY = "1.5e6"
INTERVAL_S = 0.5
STEPS_PS = [50, 100, 150, 200, 300, 600]
STEP_AT_S = 2.0
HEALTHY_SEEDS = range(11, 21)


def acquire(tmp, name, seconds, seed, *clock):
    cfg = write_json(tmp / f"{name}.json", {
        "schema_version": "2.1",
        "description": "measurement, Chapter 38",
        "source": {"type": "udp", "udp": {"address": "127.0.0.1", "port": 0}},
        "output": {"type": "none"},
        "timing_monitor": {"interval_s": INTERVAL_S},
    })
    with Server(tmp) as server:
        ctl = Ctl(server)
        ctl.ok("configure", str(cfg))
        ctl.ok("start")
        port = int(UDP_PORT.search(ctl.status()["detector"]).group(1))
        sent = subprocess.run([app("minidaq_send"), "--port", str(port), "--activity", ACTIVITY,
                               "--seconds", str(seconds), "--seed", str(seed), "--speed", "1", *clock],
                              capture_output=True, text=True, timeout=120, check=True)
        packets = int(re.search(r"packets (\d+) of", sent.stdout).group(1))
        eventually(lambda: ctl.status()["detector_counters"]["datagrams"] >= packets, 30, "the datagrams")
        ctl.ok("stop")
        ctl("wait", "configured", "30")
        status = ctl.status()
        server.stop()
    return status


def others_worst(t):
    return max(abs(b["worst_ps"]) for i, b in enumerate(t["blocks"]) if i != BLOCK)


def row(name, status):
    t = status["timing"]
    b = t["blocks"][BLOCK]
    first = "never" if b["first_alarm_s"] is None else f"{b['first_alarm_s']:.1f}"
    return (f"| {name} | {b['level']} | {b['offset_ps']:.0f} +- {b['sigma_ps']:.0f} | {first} | "
            f"{b['alarm_intervals']} | {others_worst(t):.0f} | {t['alarm_intervals']} | "
            f"{t['chi2_per_dof']:.2f} | {t['pairs']} | {'yes' if status['integrity']['complete'] else 'no'} |")


def main():
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs; build {BUILD.name}.")
    print(f"Source {ACTIVITY} Bq, intervals of {INTERVAL_S} s, baseline 2 intervals, warning 100 ps, "
          "alarm 250 ps, 5 standard deviations.")
    print()
    header = ("| Run | Block 29 level | Its offset, ps | First alarm, s | Its intervals at alarm | "
              "Largest offset of another block, ps | Intervals at alarm | chi2/dof | Pairs | Complete |")
    rule = "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        print(f"Steps of block {BLOCK}'s clock at {STEP_AT_S} s, runs of 4 s, seed 5:")
        print()
        print(header)
        print(rule)
        for ps in STEPS_PS:
            s = acquire(tmp, f"step{ps}", 4.0, 5, "--block-clock", f"{BLOCK}:0:0:{STEP_AT_S}:{ps}")
            print(row(f"step of {ps} ps", s), flush=True)
        s = acquire(tmp, "drift", 4.0, 5, "--block-clock", f"{BLOCK}:0:0.1")
        print(row("drift of 0.1 ppb (100 ps/s)", s), flush=True)
        print()
        print(f"Healthy runs of 4 s, seeds {HEALTHY_SEEDS.start} to {HEALTHY_SEEDS.stop - 1}:")
        print()
        print(header)
        print(rule)
        alarms = 0
        evaluated = 0
        largest = 0.0
        for seed in HEALTHY_SEEDS:
            s = acquire(tmp, f"healthy{seed}", 4.0, seed)
            t = s["timing"]
            alarms += t["alarm_intervals"]
            evaluated += t["intervals"] - 2
            largest = max(largest, max(abs(b["worst_ps"]) for b in t["blocks"]))
            print(row(f"seed {seed}", s), flush=True)
        print()
        print(f"Healthy: {alarms} intervals at alarm in {evaluated} evaluated intervals of 72 blocks "
              f"({evaluated * 72} block intervals); the largest offset of any block {largest:.0f} ps.")
    print()
    bm = subprocess.run([str(BUILD / "benchmarks" / "bm_timing_monitor"), "--benchmark_repetitions=5",
                         "--benchmark_report_aggregates_only=true", "--benchmark_format=json"],
                        capture_output=True, text=True, check=True)
    print("Cost (bm_timing_monitor, median of 5):")
    print()
    for b in json.loads(bm.stdout)["benchmarks"]:
        if b.get("aggregate_name") != "median":
            continue
        if b["run_name"] == "BM_TimingMonitorRecord":
            print(f"- record(): {1e9 / b['items_per_second']:.1f} ns per coincidence")
        else:
            print(f"- one fit of 72 offsets to 2,556 pairs: {b['real_time']:.0f} {b['time_unit']}")


if __name__ == "__main__":
    main()
