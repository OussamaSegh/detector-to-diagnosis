#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 29 measurements: what crossing the boundary costs (roadmap 2.1.0, Theme H).

1. A call: the time of one call of a tiny projection (4 x 4 pixels, 2 views of 5 bins), whose
   computation is negligible, against a Python function call and a NumPy operation of the same
   size. Median of 7 runs of 20,000 calls, per call.
2. A conversion: one forward projection of MiniDAQ's 2D geometry (128 x 128 pixels, 192 views of
   227 bins), 1 thread, with a C-ordered float64 image, which pybind11 passes as it is, and with
   a Fortran-ordered, a float32 and a strided one, which it converts first. Median of 15.
   The conversion is timed alone, being smaller than the spread of the projection's time.
3. An allocation: the same back projection into a new array each time and into one out= array,
   alternated, median of 15; and the allocation alone.
4. The GIL: how far a Python thread that counts gets while the main thread runs 10 forward
   projections, against while it sleeps for as long and while it runs a Python loop as long;
   the projector releases the GIL, the loop holds it. Five runs of each, alternated.

    MINIDAQ_RECON_CPP=build/release/recon python3 measurements/ch29/crossing.py \
        > measurements/ch29/crossing.txt

Use the release build's module: the debug build is unoptimized.
"""
import os
import pathlib
import platform
import statistics
import sys
import threading
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.recon import project, sinogram as sg  # noqa: E402


def median_time(f, runs):
    times = []
    for _ in range(runs):
        t = time.perf_counter()
        f()
        times.append(time.perf_counter() - t)
    return statistics.median(times)


def per_call(f, calls=20_000, runs=7):
    def many():
        for _ in range(calls):
            f()
    return median_time(many, runs) / calls


def counted(work, seconds=None):
    """How many times a Python thread counts while `work` runs in this thread."""
    ticks = 0
    done = threading.Event()
    running = threading.Event()

    def count():
        nonlocal ticks
        running.set()
        while not done.is_set():
            ticks += 1

    worker = threading.Thread(target=count)
    worker.start()
    running.wait()
    time.sleep(0.05)
    start, t = ticks, time.perf_counter()
    work()
    got, elapsed = ticks - start, time.perf_counter() - t
    done.set()
    worker.join()
    return got, elapsed


def main():
    m = project.load_cpp()
    print("# Chapter 29: what crossing the boundary costs\n")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} CPUs, Python "
          f"{platform.python_version()}, numpy {np.__version__}. Module: "
          f"{os.environ.get('MINIDAQ_RECON_CPP', '(sys.path)')}.\n")

    print("## 1. A call\n")
    tiny_s = np.array([[-3.0, -1.5, 0.0, 1.5, 3.0]] * 2)
    tiny_phi = np.array([[0.0] * 5, [np.pi / 2] * 5])
    tiny = m.Projector(tiny_s, tiny_phi, n=4, pixel_mm=2.0, threads=1)
    x4 = np.ones((4, 4))
    out = np.empty((2, 5))

    def nothing(a):
        return a

    rows = [("Python function call", per_call(lambda: nothing(x4))),
            ("NumPy `x * 2.0` on 4 x 4", per_call(lambda: x4 * 2.0)),
            ("`forward` of 4 x 4 pixels, 10 lines", per_call(lambda: tiny.forward(x4))),
            ("the same with `out=`", per_call(lambda: tiny.forward(x4, out=out))),
            ("the same with `views=[0]`", per_call(lambda: tiny.forward(x4, views=[0])))]
    print("| Call | Time per call |")
    print("|---|---:|")
    for name, t in rows:
        print(f"| {name} | {t * 1e6:.2f} µs |")
    print()

    print("## 2. A conversion\n")
    h = sg.Header(path=None, radial_bins=227, views=192, slices=1, tof_bins=1, first_r=-113,
                  max_ring_difference=0, fov_radius_mm=120.0, files={})
    s, phi = project.bin_lines(h, radius_mm=156.0)
    p = m.Projector(s, phi, n=128, pixel_mm=2.0, threads=1)
    rng = np.random.default_rng(29)
    x = rng.random((128, 128))
    big = rng.random((256, 256))
    images = [("C-ordered float64 (passed as it is)", x),
              ("Fortran-ordered float64", np.asfortranarray(x)),
              ("float32", x.astype(np.float32)),
              ("strided view, `big[::2, ::2]`", big[::2, ::2])]
    p.forward(x)  # warm up the caches and the allocator before timing
    base = median_time(lambda: p.forward(x), 15)
    print(f"One forward projection, 1 thread, of the C-ordered float64 image: "
          f"{base * 1e3:.2f} ms.\n")
    print("| Image | Its conversion alone | Share of one forward projection |")
    print("|---|---:|---:|")
    for name, img in images:
        conv = per_call(lambda img=img: np.ascontiguousarray(img, dtype=np.float64), 2_000)
        print(f"| {name} | {conv * 1e6:.1f} µs | {100 * conv / base:.2f}% |")
    print("\nThe conversion is what `c_style | forcecast` does for the module, timed on its own,"
          " because it is smaller than the spread of the projection's own time.\n")

    print("## 3. An allocation\n")
    y = rng.random(s.shape)
    image = np.empty((128, 128))
    p.back(y, out=image)
    news, intos = [], []
    for _ in range(15):  # alternate, so that both see the same state of the machine
        news.append(median_time(lambda: p.back(y), 1))
        intos.append(median_time(lambda: p.back(y, out=image), 1))
    new, into = statistics.median(news), statistics.median(intos)
    alloc = per_call(lambda: np.empty((128, 128)), 20_000)
    print("| Back projection, 1 thread | Time |")
    print("|---|---:|")
    print(f"| into a new array | {new * 1e3:.2f} ms |")
    print(f"| into one `out=` array | {into * 1e3:.2f} ms |")
    print(f"\nThe allocation alone, `np.empty((128, 128))`: {alloc * 1e6:.2f} µs, "
          f"{100 * alloc / new:.3f}% of the back projection.\n")

    print("## 4. The GIL\n")
    p4 = m.Projector(s, phi, n=128, pixel_mm=2.0, threads=1)

    def python_loop(seconds):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            pass

    rates = {"projects": [], "sleeps": [], "loops": []}
    for _ in range(5):  # alternate the three, five times
        busy, elapsed = counted(lambda: [p4.forward(x) for _ in range(10)])
        rates["projects"].append(busy / elapsed)
        idle, idle_elapsed = counted(lambda e=elapsed: time.sleep(e))
        rates["sleeps"].append(idle / idle_elapsed)
        held, held_elapsed = counted(lambda e=elapsed: python_loop(e))
        rates["loops"].append(held / held_elapsed)
    ref = statistics.median(rates["sleeps"])
    print("Counts per second of a Python thread that counts, while the main thread does each of "
          "these for about 0.3 s; 5 runs of each, alternated.\n")
    print("| While the main thread | Counts per second, median | Range | Against sleeping |")
    print("|---|---:|---:|---:|")
    for key, name in (("sleeps", "sleeps"), ("projects", "runs 10 forward projections"),
                      ("loops", "runs a Python loop as long")):
        r = rates[key]
        print(f"| {name} | {statistics.median(r):,.0f} | {min(r):,.0f} to {max(r):,.0f} | "
              f"{100 * statistics.median(r) / ref:.0f}% |")
    print("\nThe projector releases the GIL, so the other thread keeps running; a Python loop "
          "holds it, and the two threads take turns.")

if __name__ == "__main__":
    main()
