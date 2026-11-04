# Exercise 31.3 (H): The per-crystal timing histogram in C++, behind a Python boundary

**Goal.** Move the one loop of the analysis that NumPy does not vectorize well, a histogram of
the time difference per crystal, into C++ called from Python through pybind11. Keep the
boundary safe and the bin edges exactly those of the NumPy reference.

**Time.** 2 hours.

**Starter.** `starter/dthist.cpp` builds into the module `dthist`.
`histogram(crystal, dt_ps, crystals, lo_ps, bin_ps, bins)` returns `(counts, outside)`, where
`counts` is a new `uint32` array of shape `(crystals, bins)`. It takes
`py::array_t<std::int32_t, py::array::c_style>`, computes the bin with `/`, and holds the GIL for
the whole loop. Build it with `cmake -S . -B build/debug -DMINIDAQ_BUILD_STARTERS=ON
-DMINIDAQ_BUILD_RECON_PYTHON=ON` (the Python headers are needed: `python3-dev`).

**Acceptance** (`tests/test_dthist.py`, run by `ctest --test-dir build/debug -R ch31/e3`):
- On 200,000 entries, the counts and the number outside equal a NumPy reference
  (`np.floor_divide` and `np.bincount`) bin for bin.
- `lo_ps` is in the first bin; `lo_ps - 1`, `lo_ps - bin_ps + 1` and `lo_ps + bins * bin_ps` are
  outside.
- `int64` arrays are converted and give the same counts.
- Arrays of different lengths, and a crystal id beyond `crystals`, raise `ValueError`.
- On 50,000 entries, at least 15 times faster than a Python loop over the entries (the best of
  five runs each, in an optimized build).

**Then, by hand.**
1. Which entries did the starter count in the first bin that belong outside? Write the rule of
   C++ integer division for a negative numerator, and the one of Python's `//`.
2. What did the starter do with the `int64` arrays, and why does `py::array::forcecast` change
   that? What does forcecast silently do to an `int64` value that does not fit in 32 bits, and is
   that acceptable for a time difference read from MDQ-L1?
3. Time the NumPy reference against the C++ function on 10 million entries. Is the C++ worth its
   build and its binding in a package that is otherwise pure Python? Answer in `NOTES.md`.

**Hints.** `floor(a / b)` for `b > 0` is `a / b - 1` when `a % b != 0` and `a < 0`, else `a / b`.
`py::gil_scoped_release` may only cover code that touches no Python object: read the arrays
through `unchecked<1>()` views taken before it, and raise the error after it.
