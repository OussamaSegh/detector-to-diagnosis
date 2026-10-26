#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 23 measurements: receive cost per datagram by call and batch size (bm_udp_receive).

Runs the benchmark with 10 repetitions and prints, for each case, the minimum, median and maximum
time per datagram, and the payload rate at the median.

    python3 measurements/ch23/receive_cost.py build/release/benchmarks/bm_udp_receive > measurements/ch23/receive_cost.txt
"""
import json
import statistics
import subprocess
import sys

BM = sys.argv[1] if len(sys.argv) > 1 else "build/release/benchmarks/bm_udp_receive"
out = subprocess.run([BM, "--benchmark_repetitions=10", "--benchmark_format=json"], capture_output=True, text=True,
                     check=True).stdout
data = json.loads(out)
runs = {}
for b in data["benchmarks"]:
    if b.get("run_type") != "iteration" or "error_occurred" in b:
        continue
    runs.setdefault(b["run_name"], []).append(b)
ctx = data["context"]
print(f"# {ctx['num_cpus']} CPUs at {ctx['mhz_per_cpu']} MHz, {ctx['library_build_type']} library build, "
      f"128 datagrams per fill, loopback")
print("| Call | Datagram | ns per datagram (min / median / max) | Payload at the median |")
print("|---|---:|---|---:|")
for name, bs in runs.items():
    parts = dict(p.split(":") for p in name.split("/")[1:])
    per = sorted(1e9 / b["items_per_second"] for b in bs)
    rate = statistics.median(b["bytes_per_second"] for b in bs) * 8 / 1e9
    call = "recv" if parts["batch"] == "1" else f"recvmmsg, {parts['batch']}"
    print(f"| {call} | {int(parts['bytes']):,} B | {per[0]:.0f} / {statistics.median(per):.0f} / {per[-1]:.0f} |"
          f" {rate:.1f} Gbit/s |")
