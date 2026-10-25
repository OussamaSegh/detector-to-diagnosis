#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""End-to-end check of the list-mode tools (Chapter 12), run by CTest.

minidaq_sim writes a short point-source run with the DAQ's list-mode sink, in
several files; minidaq_listmode verify accepts it; one flipped byte makes
verify fail and costs exactly one block; a removed last file and a truncated
file are reported; sino writes sinograms whose counts add up to the prompts.

    python3 tools/test_listmode_tools.py build/debug/minidaq/apps
"""
import glob
import os
import struct
import subprocess
import sys
import tempfile


def run(*args, check=True):
    p = subprocess.run(list(args), capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"FAIL: {' '.join(args)} returned {p.returncode}\n{p.stdout}{p.stderr}")
    return p


def main():
    apps = sys.argv[1]
    sim = os.path.join(apps, "minidaq_sim")
    lm = os.path.join(apps, "minidaq_listmode")
    with tempfile.TemporaryDirectory() as d:
        run(sim, "--source", "point", "--centre", "40,-25,0", "--phantom", "0", "--fov", "120",
            "--activity", "2e6", "--seconds", "0.7", "--listmode", d, "--max-file-mb", "1")
        files = sorted(glob.glob(os.path.join(d, "*.mdql")))
        assert len(files) >= 2, f"expected a rotation, got {files}"
        assert not glob.glob(os.path.join(d, "*.part")), "a clean run leaves no .part file"
        run(lm, "verify", *files)
        assert run(lm, "verify", *files[:-1], check=False).returncode == 1, "the run's last file is missing"

        info = run(lm, "info", *files).stdout
        prompts = sum(int(line.split("prompts ")[1].split(",")[0]) for line in info.splitlines()
                      if "records" in line and "prompts" in line)
        assert prompts > 10_000, info

        # One flipped byte in the middle of the first file: one block lost, the rest intact.
        data = bytearray(open(files[0], "rb").read())
        data[len(data) // 2] ^= 0x40
        bad = os.path.join(d, "bad.mdql")
        open(bad, "wb").write(data)
        p = run(lm, "verify", bad, check=False)
        assert p.returncode == 1 and "damaged or missing" in p.stdout, p.stdout
        p = run(lm, "info", bad, check=False)
        assert "lost: 1 blocks" in p.stdout, p.stdout

        # A file cut in the middle of a block, as a crash would leave it.
        cut = os.path.join(d, "cut.mdql.part")
        open(cut, "wb").write(bytes(data[: len(data) // 3]))
        p = run(lm, "info", cut, check=False)
        assert p.returncode == 1 and "no closing block" in p.stdout, p.stdout
        os.remove(bad)
        os.remove(cut)

        out = os.path.join(d, "s")
        p = run(lm, "sino", "--out", out, *files)
        binned = int(p.stdout.split("binned ")[1].split(" ")[0])
        assert binned == prompts, (binned, prompts)
        raw = open(out + ".prompts2d.u32", "rb").read()
        assert len(raw) == 192 * 227 * 4
        assert sum(struct.unpack(f"<{len(raw) // 4}I", raw)) == binned
        header = open(out + ".hdr").read()
        assert "matrix size [radial] := 227" in header and "!END OF INTERFILE :=" in header, header
    print("list-mode tools: ok")


if __name__ == "__main__":
    main()
