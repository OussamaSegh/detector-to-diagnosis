#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 12: list-mode writer throughput on this machine's disk, per fsync policy.

Each run writes coincidences through the DAQ's list-mode sink (16-byte records
in 64 KiB blocks), as fast as the sink accepts them, and times it to the end of
close(), when the policy's fsyncs are done. Short runs (20 M coincidences,
320 MB) fit in the page cache, which takes them at memory speed until the
fsync; long runs (200 M, 3.2 GB) are larger than the kernel lets dirty pages
grow (vm.dirty_ratio of the RAM), so they measure what the disk sustains. The
baseline is dd of the same amount with one fsync at the end. The files are
deleted after each run.

    python3 measurements/ch12/writer.py build/release /var/tmp/minidaq-bench > measurements/ch12/writer.txt

The numbers describe this VM's virtual disk; a real acquisition disk (NVMe,
RAID) needs its own run (assumption: confirm with team which disk NeuroLF
writes to).
"""
import os
import platform
import re
import shutil
import subprocess
import sys

BUILD = sys.argv[1] if len(sys.argv) > 1 else "build/release"
DIR = sys.argv[2] if len(sys.argv) > 2 else "/var/tmp/minidaq-bench"
TOOL = os.path.join(BUILD, "benchmarks", "writer_throughput")
REPEATS = 3
SHORT = [
    ("none", 256, 64),
    ("close", 256, 64),
    ("interval", 1024, 64),  # 64 MiB between fsyncs
    ("interval", 256, 64),   # 16 MiB
    ("interval", 64, 64),    # 4 MiB
    ("interval", 16, 64),    # 1 MiB
    ("close", 256, 4),       # a small pool
]
LONG = [
    ("none", 256, 64),
    ("close", 256, 64),
    ("interval", 256, 64),
    ("interval", 16, 64),
    ("close", 256, 4),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def fresh():
    shutil.rmtree(DIR, ignore_errors=True)
    os.makedirs(DIR)


def main():
    print(__doc__.split("\n\n")[0])
    print(f"# {platform.node()}, {sh('nproc')} vCPU, kernel {platform.release()}")
    print(f"# {sh(f'findmnt -no SOURCE,FSTYPE,OPTIONS -T {os.path.dirname(DIR) or DIR}')}")
    print(f"# {sh('lsblk -dno NAME,SIZE,ROTA,MODEL 2>/dev/null | head -3')}")
    print()
    print(f"# RAM {sh('free -g | awk \'/Mem:/ {print $2}\'')} GiB, vm.dirty_ratio {sh('sysctl -n vm.dirty_ratio')}%, "
          f"vm.dirty_background_ratio {sh('sysctl -n vm.dirty_background_ratio')}%")
    print()
    for label, n, mib, runs, repeats in (("short", "20e6", 305, SHORT, REPEATS), ("long", "200e6", 3052, LONG, 2)):
        print(f"== {label}: baseline dd {mib} MiB in 1 MiB writes, one fsync at the end (conv=fsync)")
        for _ in range(repeats):
            fresh()
            out = subprocess.run(["dd", "if=/dev/zero", f"of={DIR}/dd.bin", "bs=1M", f"count={mib}", "conv=fsync"],
                                 capture_output=True, text=True).stderr.strip().splitlines()[-1]
            print("  " + out)
        print()
        print(f"== {label}: list-mode sink, {float(n) / 1e6:.0f} M coincidences per run")
        for fsync, every, buffers in runs:
            rates = []
            for _ in range(repeats):
                fresh()
                out = subprocess.run([TOOL, "--dir", DIR, "--coincidences", n, "--fsync", fsync, "--every",
                                      str(every), "--buffers", str(buffers), "--max-file-mb", "1024"],
                                     capture_output=True, text=True, check=True).stdout
                print("  " + out.strip())
                rates.append(float(re.search(r"([0-9.]+) M/s", out).group(1)))
                sys.stdout.flush()
            rates.sort()
            mid = len(rates) // 2
            median = rates[mid] if len(rates) % 2 else (rates[mid - 1] + rates[mid]) / 2
            print(f"  -> {label} fsync={fsync} every={every} buffers={buffers}: median {median:.2f} M/s "
                  f"(min {rates[0]:.2f}, max {rates[-1]:.2f}, {len(rates)} runs)")
            print()
    shutil.rmtree(DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
