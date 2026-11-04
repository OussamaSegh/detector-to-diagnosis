#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build times of the release preset (Chapter 32).

Configures a fresh build directory with the release preset (the dependencies' sources come from
the shared .deps directory, so nothing is downloaded), then times: the configure, the clean build
of every target, a build with nothing to do, and the rebuild after touching each of four files,
from a header that 39 files include directly to one application's source. Each rebuild reports
the number of commands Ninja ran. Writes the results to stdout.

    build_times.py SOURCE_DIR WORK_DIR [JOBS]
"""
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time

SOURCE = pathlib.Path(sys.argv[1]).resolve()
WORK = pathlib.Path(sys.argv[2]).resolve()
JOBS = sys.argv[3] if len(sys.argv) > 3 else str(os.cpu_count())
TOUCHED = ["minidaq/include/minidaq/core/expected.hpp", "minidaq/include/minidaq/core/crc32.hpp",
           "minidaq/src/core/crc32.cpp", "minidaq/apps/minidaq_send.cpp"]


def run(cmd):
    t = time.monotonic()
    r = subprocess.run(cmd, cwd=SOURCE, capture_output=True, text=True)
    elapsed = time.monotonic() - t
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    steps = re.findall(r"^\[(\d+)/(\d+)\]", r.stdout, re.M)
    return elapsed, (int(steps[-1][1]) if steps else 0)


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    cxx = subprocess.run(["c++", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    print(f"machine: {platform.machine()}, {os.cpu_count()} CPUs; {cxx}; jobs {JOBS}")
    print(f"commit: {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=SOURCE, capture_output=True, text=True).stdout.strip()}")
    t, _ = run(["cmake", "--preset", "release", "-B", str(WORK)])
    print(f"configure (fresh directory, sources present): {t:7.1f} s")
    t, n = run(["cmake", "--build", str(WORK), "-j", JOBS])
    print(f"clean build of every target:                 {t:7.1f} s, {n} commands")
    t, n = run(["cmake", "--build", str(WORK), "-j", JOBS])
    print(f"build with nothing to do:                    {t:7.1f} s, {n} commands")
    for f in TOUCHED:
        os.utime(SOURCE / f)
        t, n = run(["cmake", "--build", str(WORK), "-j", JOBS])
        print(f"after touching {f}: {t:7.1f} s, {n} commands")


if __name__ == "__main__":
    main()
