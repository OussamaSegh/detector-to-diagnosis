#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 31: four ways to fill the per-crystal timing histogram.

The histogram of Exercise 31.3: counts[c, k] for crystal c and time bin k. Four implementations of
the same thing, checked against each other bin for bin and timed:

- a Python loop over the entries (the reference of the exercise's test);
- NumPy: a floor division and one np.bincount on crystal * bins + bin;
- Numba: the Python loop compiled by @njit (the first call compiles; it is timed separately);
- C++: Exercise 31.3's solution, the module dthist, built with MINIDAQ_BUILD_RECON_PYTHON.

Usage: histogram_speed.py DTHIST_DIR [ENTRIES]
  DTHIST_DIR: the directory holding the solution's module, for instance
              build/release/exercises/ch31/e3_histogram_solution
"""
from __future__ import annotations

import platform
import statistics
import sys
import time

import numpy as np

CRYSTALS, LO, BIN, BINS = 576, -2000, 20, 200


def python_loop(crystal, dt):
    counts = [[0] * BINS for _ in range(CRYSTALS)]
    outside = 0
    for c, t in zip(crystal.tolist(), dt.tolist(), strict=True):
        k = (t - LO) // BIN
        if 0 <= k < BINS:
            counts[c][k] += 1
        else:
            outside += 1
    return np.array(counts, dtype=np.uint32), outside


def with_numpy(crystal, dt):
    k = np.floor_divide(dt.astype(np.int64) - LO, BIN)
    inside = (k >= 0) & (k < BINS)
    flat = np.bincount(crystal[inside].astype(np.int64) * BINS + k[inside],
                       minlength=CRYSTALS * BINS)
    return flat.reshape(CRYSTALS, BINS).astype(np.uint32), int(np.count_nonzero(~inside))


def numba_version():
    import numba

    @numba.njit(cache=False)
    def fill(crystal, dt, counts):
        outside = 0
        for i in range(crystal.size):
            k = (np.int64(dt[i]) - LO) // BIN  # Numba's // on integers floors, as Python's
            if 0 <= k < BINS:
                counts[crystal[i], k] += 1
            else:
                outside += 1
        return outside

    def run(crystal, dt):
        counts = np.zeros((CRYSTALS, BINS), dtype=np.uint32)
        outside = fill(crystal, dt, counts)
        return counts, int(outside)

    return run, numba.__version__


def timed(f, *args, repeat=5):
    times = []
    out = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        out = f(*args)
        times.append(time.perf_counter() - t0)
    return out, min(times), statistics.median(times)


def main(argv):
    sys.path.insert(0, argv[1])
    import dthist

    n = int(argv[2]) if len(argv) > 2 else 10_000_000
    rng = np.random.default_rng(31)
    crystal = rng.integers(0, CRYSTALS, n).astype(np.int32)
    dt = np.rint(rng.normal(-40, 300, n)).astype(np.int32)

    numba_run, numba_v = numba_version()
    t0 = time.perf_counter()
    numba_run(crystal[:10], dt[:10])
    compile_s = time.perf_counter() - t0

    print("# Chapter 31 measurements: filling the per-crystal timing histogram")
    print()
    print(f"machine: {platform.machine()}, Python {platform.python_version()}, numpy "
          f"{np.__version__}, numba {numba_v}; one thread")
    print(f"{n:,} entries (int32 crystal and dt_ps, dt normal with sigma 300 ps), {CRYSTALS} "
          f"crystals x {BINS} bins of {BIN} ps from {LO} ps; time = min and median of 5 runs")
    print()
    loop_n = min(n, 1_000_000)
    ref, t_loop, m_loop = timed(python_loop, crystal[:loop_n], dt[:loop_n], repeat=3)
    rows = [("Python loop", loop_n, t_loop, m_loop)]
    want = with_numpy(crystal[:loop_n], dt[:loop_n])
    assert np.array_equal(ref[0], want[0]) and ref[1] == want[1]

    full = with_numpy(crystal, dt)
    for name, f in (("NumPy floor_divide + bincount", with_numpy),
                    ("Numba @njit (after compiling)", numba_run),
                    ("C++ through pybind11 (dthist)",
                     lambda c, t: dthist.histogram(c, t, CRYSTALS, LO, BIN, BINS))):
        out, t, m = timed(f, crystal, dt)
        assert np.array_equal(out[0], full[0]) and out[1] == full[1], name
        rows.append((name, n, t, m))

    print("| implementation | entries | time, ms (min, median) | ns per entry | vs NumPy |")
    print("|---|---|---|---|---|")
    numpy_ns = rows[1][2] / rows[1][1] * 1e9
    for name, count, t, m in rows:
        ns = t / count * 1e9
        print(f"| {name} | {count:,} | {t * 1e3:,.1f}, {m * 1e3:,.1f} | {ns:.1f} | {numpy_ns / ns:.2f}x |")
    print()
    print(f"Numba's first call, which compiles the function: {compile_s:.2f} s")
    print("Every implementation gives the same counts and the same number outside, bin for bin.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
