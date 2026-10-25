#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 12: list mode to sinograms, end to end, for the chapter's figure.

Simulates two acquisitions with minidaq_sim --listmode, histograms each with
minidaq_listmode sino, and keeps the 2D sinograms (all slices summed) and the
Michelogram, zlib-compressed, in measurements/ch12/sino/:
  - point: 1 s of a 2 MBq point source at (40, -25, 0) mm in air;
  - cylinder: 2 s of 20 MBq in a uniform cylinder of radius 80 mm and length
    100 mm, inside a water cylinder of radius 100 mm and length 180 mm.

    python3 measurements/ch12/sinogram.py build/release > measurements/ch12/sinogram.txt
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import zlib

BUILD = sys.argv[1] if len(sys.argv) > 1 else "build/release"
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = {
    "point": ["--source", "point", "--centre", "40,-25,0", "--phantom", "0", "--activity", "2e6", "--seconds", "1"],
    "cylinder": ["--source", "cylinder", "--phantom", "100", "--activity", "20e6", "--seconds", "2"],
}


def main():
    sim = os.path.join(BUILD, "minidaq", "apps", "minidaq_sim")
    lm = os.path.join(BUILD, "minidaq", "apps", "minidaq_listmode")
    print(__doc__.split("\n\n")[0])
    os.makedirs(os.path.join(HERE, "sino"), exist_ok=True)
    for name, args in RUNS.items():
        tmp = tempfile.mkdtemp(prefix="mdq-sino-")
        try:
            cmd = [sim, *args, "--seed", "12", "--fov", "120", "--listmode", tmp]
            out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
            files = sorted(glob.glob(os.path.join(tmp, "*.mdql")))
            sino = subprocess.run([lm, "sino", "--out", os.path.join(tmp, "s"), *files], check=True,
                                  capture_output=True, text=True).stdout
            size = sum(os.path.getsize(f) for f in files)
            print(f"\n== {name}: minidaq_sim {' '.join(args)} --seed 12 --fov 120")
            print("  " + next(line for line in out.splitlines() if line.startswith("countrate")))
            print(f"  list mode: {len(files)} file(s), {size} bytes")
            for line in sino.splitlines():
                print("  " + line.replace(tmp + "/", ""))
            for suffix in ("prompts2d.u32", "michelogram.u64"):
                with open(os.path.join(tmp, f"s.{suffix}"), "rb") as f:
                    data = f.read()
                with open(os.path.join(HERE, "sino", f"{name}.{suffix}.z"), "wb") as f:
                    f.write(zlib.compress(data, 9))
            shutil.copy(os.path.join(tmp, "s.hdr"), os.path.join(HERE, "sino", f"{name}.hdr"))
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
