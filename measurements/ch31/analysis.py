#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 31 measurements: the analysis package.

1. Memory and time of three ways to read a large list-mode file: tools/recon's reader (the whole
   file in memory), ListModeFile.coincidences() (mapped, decoded whole), and one pass of
   RunHistograms over chunks of 2^20 records. Each runs in its own process; the parent samples
   the child's /proc status every 5 ms and reports the peak of its anonymous memory (RssAnon, the
   memory a process really owns) and of its file-backed memory (RssFile, pages of the mapped file
   that the kernel can drop at any time). The file is synthetic, written by this script.
2. Bias and errors of the two estimators: a Gaussian photopeak on a flat background, Poisson
   counts, from 100 to 100,000 counts in the peak, 400 histograms each.
3. The QC report of minidaq_sim's detector (12% energy resolution, CTR 300 ps): five seeds of a
   point source in air at 1 MBq for 2 s; the spread of the results against their reported errors.
4. Why the time resolution comes out above 300 ps: the same source with --ctr 0, which leaves only
   the photons' flight inside the crystals (depth of interaction).

    python3 measurements/ch31/analysis.py BUILD_APPS_DIR WORK_DIR [PARTS] > measurements/ch31/analysis.txt

PARTS is a comma-separated list of 1, 2 and 3 (3 includes 4); the default is all of them.

BUILD_APPS_DIR holds minidaq_sim (a release build). WORK_DIR receives about 1.2 GB.
"""
import json
import math
import os
import pathlib
import platform
import statistics
import subprocess
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "src"))
from minidaq_analysis import fitting as F  # noqa: E402
from minidaq_analysis import listmode  # noqa: E402

LARGE_RECORDS = 64 * 1024 * 1024  # 1 GiB of records
BLOCK = 65_536
SIGMA_TO_FWHM = F.SIGMA_TO_FWHM


def section(title):
    print(f"\n## {title}\n", flush=True)


# ------------------------------------------------------------------------------------------------
# 1. A large file, written with numpy (the test writer packs one record at a time: too slow here).

def write_large(path, n, seed=1):
    meta = json.dumps({"format": "MDQ-L1", "software": "measurements/ch31", "simulated": True,
                       "created_utc": "2026-11-03T08:00:00Z",
                       "file": {"segment": 0, "run_name": "large"},
                       "scanner": {"crystals_per_ring": 576, "crystal_rings": 32},
                       "records": {"time_unit": "ps", "energy_lsb_kev": 0.03125,
                                   "delayed_window_ps": 100000,
                                   "coincidence_window_ps": 4000}}).encode()
    pad = (len(meta) + 7) & ~7
    head = (b"MDQL\r\n\x1a\n" + (1).to_bytes(2, "little") + (0).to_bytes(2, "little")
            + (40 + pad).to_bytes(4, "little") + len(meta).to_bytes(4, "little")
            + (0).to_bytes(4, "little") + (16).to_bytes(4, "little") + (0).to_bytes(4, "little")
            + meta + b"\0" * (pad - len(meta)))
    head += zlib.crc32(head).to_bytes(4, "little") + b"\0\0\0\0"
    rng = np.random.default_rng(seed)
    with open(path, "wb") as f:
        f.write(head)
        seq = 0
        t = 0
        for start in range(0, n, BLOCK):
            k = min(BLOCK, n - start)
            r = np.zeros(k, dtype=listmode.RECORD)
            gaps = rng.integers(1, 30_000, k)  # about 66 ns apart: 15 M coincidences/s
            offsets = np.cumsum(gaps) - gaps[0]
            r["time_offset"] = offsets
            # Pairs as a centered source gives them: the second crystal across the ring from the
            # first (within 20 crystals) and within 3 rings of it.
            a = rng.integers(0, 18432, k)
            across = (a % 576 + 288 + rng.integers(-20, 21, k)) % 576
            ring = np.clip(a // 576 + rng.integers(-3, 4, k), 0, 31)
            r["crystal_a"] = a
            r["crystal_b"] = ring * 576 + across
            r["dt_ps"] = rng.integers(0, 2000, k)
            r["energy_a"] = rng.integers(435 * 32, 585 * 32, k)
            r["energy_b"] = rng.integers(435 * 32, 585 * 32, k)
            payload = r.tobytes()
            h = (b"MDQB" + seq.to_bytes(4, "little") + k.to_bytes(4, "little")
                 + (0).to_bytes(4, "little") + t.to_bytes(8, "little", signed=True)
                 + zlib.crc32(payload).to_bytes(4, "little"))
            f.write(h + zlib.crc32(h).to_bytes(4, "little") + payload)
            t += int(offsets[-1]) + 1
            seq += 1
        h = (b"MDQB" + seq.to_bytes(4, "little") + (0).to_bytes(4, "little")
             + (1).to_bytes(4, "little") + (0).to_bytes(8, "little")
             + zlib.crc32(b"").to_bytes(4, "little"))
        f.write(h + zlib.crc32(h).to_bytes(4, "little"))


READERS = {
    "recon read_file (whole file in memory)": """
import sys; sys.path.insert(0, ROOT)
from tools.recon import listmode
meta, c = listmode.read_file(PATH)
n = len(c["time_ps"])""",
    "ListModeFile.coincidences() (mapped, decoded whole)": """
import sys; sys.path.insert(0, ROOT + "/analysis/src")
from minidaq_analysis.listmode import ListModeFile
with ListModeFile(PATH) as f:
    n = len(f.coincidences())""",
    "RunHistograms over chunks of 2^20 records (mapped)": """
import sys; sys.path.insert(0, ROOT + "/analysis/src")
from minidaq_analysis.listmode import ListModeFile
from minidaq_analysis.histograms import RunHistograms
h = RunHistograms(18432, 100000)
with ListModeFile(PATH) as f:
    for c, tags in f.chunks(1 << 20):
        h.add(c, tags)
n = h.prompts + h.delayeds""",
    "RunHistograms over chunks of 2^20 records, without pair counts (mapped)": """
import sys; sys.path.insert(0, ROOT + "/analysis/src")
from minidaq_analysis.listmode import ListModeFile
from minidaq_analysis.histograms import RunHistograms
h = RunHistograms(18432, 100000, count_pairs=False)
with ListModeFile(PATH) as f:
    for c, tags in f.chunks(1 << 20):
        h.add(c, tags)
n = h.prompts + h.delayeds""",
    "ListModeFile opened and every payload CRC checked, nothing decoded (mapped)": """
import sys; sys.path.insert(0, ROOT + "/analysis/src")
from minidaq_analysis.listmode import ListModeFile
with ListModeFile(PATH) as f:
    n = f.records_total""",
}


def status_kb(pid, field):
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith(field + ":"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def measure_reader(code, path):
    prog = f"ROOT = {str(ROOT)!r}\nPATH = {str(path)!r}\n" + code + "\nprint(n)"
    t0 = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-c", prog], stdout=subprocess.PIPE, text=True)
    anon = file_ = 0
    while p.poll() is None:
        anon = max(anon, status_kb(p.pid, "RssAnon"))
        file_ = max(file_, status_kb(p.pid, "RssFile"))
        time.sleep(0.005)
    out = p.stdout.read().strip()
    return time.perf_counter() - t0, anon / 1024, file_ / 1024, int(out) if out else -1


def part1(work):
    section("1. Reading a 1 GiB list-mode file")
    path = work / "large.mdql"
    if not path.exists() or path.stat().st_size < LARGE_RECORDS * 16:
        write_large(path, LARGE_RECORDS)
    print(f"file: {path.stat().st_size:,} bytes, {LARGE_RECORDS:,} records, "
          f"{LARGE_RECORDS // BLOCK:,} blocks; synthetic: crystal pairs across the ring as from a centered source, uniform energies")
    print("each reader runs three times in a fresh process; the file is in the page cache after "
          "the first run (the machine has enough memory)")
    print(f"\n| reader | time, s (min, median, max) | peak RssAnon, MiB | peak RssFile, MiB | "
          "coincidences |")
    print("|---|---|---|---|---|")
    measure_reader(READERS["RunHistograms over chunks of 2^20 records (mapped)"], path)  # warm
    for name, code in READERS.items():
        runs = [measure_reader(code, path) for _ in range(3)]
        times = sorted(r[0] for r in runs)
        print(f"| {name} | {times[0]:.1f}, {statistics.median(times):.1f}, {times[-1]:.1f} | "
              f"{max(r[1] for r in runs):,.0f} | {max(r[2] for r in runs):,.0f} | "
              f"{runs[0][3]:,} |", flush=True)


# ------------------------------------------------------------------------------------------------
# 2. Estimator bias.

def part2():
    section("2. Neyman least squares against Poisson maximum likelihood")
    edges = np.arange(400.0, 621.0, 1.0)
    model = F.gaussian_plus_line(400.0, 620.0)
    rng = np.random.default_rng(2)
    print("Gaussian peak, mean 511 keV, sigma 26 keV, on a flat background of 2% of the peak's "
          "height; fit range 440 to 580 keV in 1 keV bins (140 bins); 400 histograms per row.")
    print("bias = mean(estimate) / truth - 1; pull SD = SD of (estimate - truth) / error\n")
    print("| counts in peak | peak counts per bin at the top | area bias, Neyman | "
          "area bias, Poisson | sigma bias, Neyman | sigma bias, Poisson | area pull SD, "
          "Neyman | area pull SD, Poisson | failed fits (N, P) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for area in (100, 300, 1_000, 3_000, 10_000, 100_000):
        top = area / (26.0 * math.sqrt(2 * math.pi))
        truth = np.array([area, 511.0, 26.0, 0.02 * top, 0.02 * top])
        mu = model(edges[:-1], edges[1:], truth)
        res = {"neyman": [], "poisson": []}
        failed = {"neyman": 0, "poisson": 0}
        for _ in range(400):
            h = F.Histogram(rng.poisson(mu).astype(float), edges)
            for m in res:
                try:
                    r = F.fit_photopeak(h, 440.0, 580.0, m)
                except (RuntimeError, ValueError):
                    failed[m] += 1
                    continue
                res[m].append((r["area"][0], r["area"][1], r["sigma"][0]))
        cells = []
        for key in ("area", "sigma"):
            for m in ("neyman", "poisson"):
                a = np.array(res[m])
                col, true = (0, area) if key == "area" else (2, 26.0)
                cells.append(f"{100 * (a[:, col].mean() / true - 1):+.1f}%")
        for m in ("neyman", "poisson"):
            a = np.array(res[m])
            cells.append(f"{np.std((a[:, 0] - area) / a[:, 1], ddof=1):.2f}")
        print(f"| {area:,} | {top:.1f} | " + " | ".join(cells)
              + f" | {failed['neyman']}, {failed['poisson']} |", flush=True)


# ------------------------------------------------------------------------------------------------
# 3 and 4. The simulator.

def simulate(apps, work, name, extra, seed):
    d = work / name
    if not list(d.glob("*.run.json")):
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "sim.txt", "w") as out:
            subprocess.run([str(apps / "minidaq_sim"), "--source", "point", "--phantom", "0",
                            "--activity", "1e6", "--seconds", "2", "--seed", str(seed),
                            "--listmode", str(d), *extra], check=True, stdout=out)
    return next(d.glob("*.run.json"))


def qc(record, out):
    p = subprocess.run([sys.executable, "-m", "minidaq_analysis", str(record), str(out)],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "analysis" / "src")))
    if p.returncode not in (0, 1):
        raise SystemExit(p.stderr)
    return json.loads((out / "report.json").read_text())


def part3(apps, work):
    section("3. The QC report on minidaq_sim's point source (five seeds)")
    print("minidaq_sim --source point --phantom 0 --activity 1e6 --seconds 2 --seed N: the "
          "simulator's detector has an energy resolution of 12% FWHM at 511 keV and blurs each "
          "single's time so that a pair has 300 ps FWHM\n")
    print("| seed | result | prompts | photopeak, keV | FWHM/E, % | CTR FWHM, ps | timing center, "
          "ps | photopeak deviance/ndf | timing deviance/ndf | p constant | p dip |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    rows = []
    for seed in range(1, 6):
        rep = qc(simulate(apps, work, f"point-{seed}", [], seed), work / f"qc-{seed}")
        c = {x["name"]: x for x in rep["checks"]}
        e, t = rep["fits"]["photopeak"], rep["fits"]["timing"]
        res = c["energy resolution (FWHM/E)"]
        ctr = c["coincidence time resolution (FWHM)"]
        rows.append((res["value"], res["error"], ctr["value"], ctr["error"]))
        print(f"| {seed} | {'pass' if rep['passed'] else 'FAIL'} | {rep['run']['prompts']:,} | "
              f"{e['parameters']['mean']:.2f} ± {e['errors']['mean']:.2f} | "
              f"{100 * res['value']:.3f} ± {100 * res['error']:.3f} | "
              f"{ctr['value']:.1f} ± {ctr['error']:.1f} | "
              f"{t['parameters']['mean']:+.2f} ± {t['errors']['mean']:.2f} | "
              f"{e['statistic'] / e['ndf']:.3f} | {t['statistic'] / t['ndf']:.3f} | "
              f"{c['prompt rate constant (p)']['value']:.3f} | "
              f"{c['no dip in the prompt rate (p)']['value']:.3f} |", flush=True)
    a = np.array(rows)
    print(f"\nFWHM/E over the seeds: mean {100 * a[:, 0].mean():.3f}%, SD "
          f"{100 * a[:, 0].std(ddof=1):.3f}%; mean reported error {100 * a[:, 1].mean():.3f}%")
    print(f"CTR over the seeds: mean {a[:, 2].mean():.1f} ps, SD {a[:, 2].std(ddof=1):.1f} ps; "
          f"mean reported error {a[:, 3].mean():.1f} ps")
    return a


def part4(apps, work, a):
    section("4. Where the extra picoseconds come from")
    record = simulate(apps, work, "point-ctr0", ["--ctr", "0"], 1)
    c = listmode.Run(record).coincidences()
    p = c.select(~c.delayed)
    from minidaq_analysis.histograms import signed_dt_ps
    s = signed_dt_ps(p).astype(float)
    sd0 = float(np.std(s, ddof=1))
    q = np.percentile(s, [25, 50, 75])
    print("minidaq_sim with --ctr 0: no time blur; what remains is the flight of each photon "
          "inside its crystal to the point where it interacts (the simulator adds path length "
          "to the depth of interaction)")
    print(f"prompts {len(p):,}; signed time difference: SD {sd0:.1f} ps, quartiles "
          f"{q[0]:.0f}, {q[1]:.0f}, {q[2]:.0f} ps")
    blur_sd = 300.0 / SIGMA_TO_FWHM
    total_sd = math.sqrt(blur_sd**2 + sd0**2)
    print(f"variances add under convolution: SD sqrt({blur_sd:.1f}^2 + {sd0:.1f}^2) = "
          f"{total_sd:.1f} ps, which as a Gaussian is a FWHM of {SIGMA_TO_FWHM * total_sd:.1f} ps")
    print(f"measured in section 3: {a[:, 2].mean():.1f} ps (the fit is of the core of the peak, "
          "so it weighs the depth's long tail less than the SD does)")


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    apps, work = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    print("# Chapter 31 measurements: the analysis package")
    print(f"\nmachine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}; "
          f"{time.strftime('%Y-%m-%d', time.gmtime())}")
    parts = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else {"1", "2", "3"}
    if "1" in parts:
        part1(work)
    if "2" in parts:
        part2()
    if "3" in parts:
        a = part3(apps, work)
        part4(apps, work, a)


if __name__ == "__main__":
    main()
