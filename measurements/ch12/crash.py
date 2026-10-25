#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 12: kill -9 the list-mode writer at random moments; what survives?

Each trial starts writer_throughput --forever (5 M coincidences per second of
data time, 200 us apart, files rotated every 64 MiB, fsync every 16 blocks),
kills it with SIGKILL after a random 0.2 to 2 s, and reads every file it left
with an independent reader written here from the specification (Python's
struct and zlib.crc32, not the C++ code):
  - every completed file (.mdql) must be intact and end with a closing block;
  - at most one .part file, intact up to a possibly truncated last block;
  - the records of all files together must be exactly the first N coincidences
    the writer produced, with no gap and no duplicate.

    python3 measurements/ch12/crash.py build/release /var/tmp/minidaq-crash > measurements/ch12/crash.txt

SIGKILL ends the process, not the machine: what the process had passed to
write(2) is in the page cache and reaches the disk. A power loss can lose
what was not yet fsynced, which this test cannot show (verify: with a
power-cut rig or a block-layer fault injector such as dm-log-writes).
"""
import glob
import os
import random
import shutil
import signal
import struct
import subprocess
import sys
import time
import zlib

BUILD = sys.argv[1] if len(sys.argv) > 1 else "build/release"
DIR = sys.argv[2] if len(sys.argv) > 2 else "/var/tmp/minidaq-crash"
TRIALS = int(sys.argv[3]) if len(sys.argv) > 3 else 20
SPACING_PS = 200_000


def read_mdql(data):
    """Returns (first times of the records, end flags of the last block, problems)."""
    problems = []
    if data[:8] != b"MDQL\r\n\x1a\n":
        return [], 0, ["bad file magic"]
    major, minor, header_bytes, meta_bytes = struct.unpack_from("<HHII", data, 8)
    if major != 1 or len(data) < header_bytes:
        return [], 0, ["bad version or short header"]
    if zlib.crc32(data[: header_bytes - 8]) != struct.unpack_from("<I", data, header_bytes - 8)[0]:
        return [], 0, ["bad header CRC"]
    pos, seq, times, flags = header_bytes, 0, [], 0
    while pos < len(data):
        if len(data) - pos < 32:
            problems.append(f"truncated block header at {pos}")
            break
        magic, s, n, f, base, pcrc, hcrc = struct.unpack_from("<4sIIIqII", data, pos)
        if magic != b"MDQB" or zlib.crc32(data[pos : pos + 28]) != hcrc:
            problems.append(f"bad block header at {pos}")
            break
        end = pos + 32 + 16 * n
        if end > len(data):
            problems.append(f"truncated block at {pos}")
            break
        if zlib.crc32(data[pos + 32 : end]) != pcrc:
            problems.append(f"bad payload CRC at {pos}")
            break
        if s != seq:
            problems.append(f"sequence {s} where {seq} was expected")
        seq = s + 1
        for (offset,) in struct.iter_unpack("<I12x", data[pos + 32 : end]):
            times.append(base + offset)
        flags = f
        pos = end
    return times, flags, problems


def main():
    tool = os.path.join(BUILD, "benchmarks", "writer_throughput")
    random.seed(12)
    print(__doc__.split("\n\n")[0])
    print(f"{'trial':>5} {'killed after':>12} {'files':>5} {'part':>4} {'records':>10} {'MB':>7} "
          f"{'part tail':>24}  result")
    failures = 0
    for trial in range(TRIALS):
        shutil.rmtree(DIR, ignore_errors=True)
        os.makedirs(DIR)
        p = subprocess.Popen([tool, "--dir", DIR, "--forever", "1", "--fsync", "interval", "--every", "16",
                              "--max-file-mb", "64"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        delay = random.uniform(0.2, 2.0)
        time.sleep(delay)
        p.send_signal(signal.SIGKILL)
        p.wait()
        done = sorted(glob.glob(os.path.join(DIR, "*.mdql")))
        parts = sorted(glob.glob(os.path.join(DIR, "*.mdql.part")))
        times, issues, tail, size = [], [], "", 0
        for f in done:
            data = open(f, "rb").read()
            size += len(data)
            t, flags, problems = read_mdql(data)
            times += t
            if problems or flags != 2:
                issues.append(f"{os.path.basename(f)}: {problems or 'no closing block'}")
        if len(parts) > 1:
            issues.append(f"{len(parts)} .part files")
        for f in parts:
            data = open(f, "rb").read()
            size += len(data)
            t, flags, problems = read_mdql(data)
            times += t
            if any("truncated" not in x for x in problems) or len(problems) > 1:
                issues.append(f"{os.path.basename(f)}: {problems}")
            tail = problems[0].split(" at ")[0] if problems else ("closing block" if flags else "block boundary")
        expected = [i * SPACING_PS for i in range(len(times))]
        if times != expected:
            issues.append("records are not the writer's first N coincidences")
        ok = not issues
        failures += 0 if ok else 1
        print(f"{trial:>5} {delay:>10.2f} s {len(done):>5} {len(parts):>4} {len(times):>10} {size / 1e6:>7.1f} "
              f"{tail:>24}  {'ok' if ok else '; '.join(issues)}")
        sys.stdout.flush()
    shutil.rmtree(DIR, ignore_errors=True)
    print(f"{TRIALS - failures} of {TRIALS} trials recovered every record the writer had written, in order")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
