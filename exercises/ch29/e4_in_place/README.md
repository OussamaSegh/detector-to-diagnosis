# Exercise 29.4 (M): Write into the caller's array, without a copy and without the GIL

**Goal.** Write a C++ function that adds into an array the Python caller owns: no copy of the
output, the caller's memory written in place, Python's other threads free to run while the C++
computes, and every output the C++ cannot write in place refused instead of silently copied. An
OSEM loop that reuses one image buffer per iteration needs exactly this.

**Time.** 45 minutes.

**Starter.** `starter/scatter.cpp` builds into the module `scatter`. `scatter_add(values, index,
out)` should add `values[k]` to `out[index[k]]` for every `k`, in place, and return `None`. It
takes all three arrays as `py::array_t<double, c_style | forcecast>` (the index as int64), holds
the GIL for the whole loop and checks nothing. Build it with
`cmake -S . -B build/debug -DMINIDAQ_BUILD_STARTERS=ON` (the Python headers are needed:
`python3-dev`).

**Acceptance** (`tests/test_scatter.py`, run by `ctest --test-dir build/debug -R ch29/e4`):
- The sums are in the caller's float64 array, also when it is two-dimensional or the C-contiguous
  rows of a larger one; a second call adds to the first.
- Inputs of other dtypes (float32 values, int32 indices) are converted.
- A float32, a Fortran-ordered or a strided `out` raises `ValueError` saying what it must be, a
  read-only one says so, a list raises `TypeError`; the caller's array is unchanged.
- An index outside `out` raises `IndexError` with the position and the value, before any write;
  `values` and `index` of different lengths raise `ValueError`.
- Another Python thread keeps running during a call of 3e7 additions.

**Then, by hand.**
1. What did the starter do with a float32 `out`, and what did the caller see?
2. What did the starter write for an index of 50 into 50 elements? Why is that worse than a
   crash?
3. While the GIL is released, another Python thread may change `out`. What would the caller find,
   and whose mistake is it? Answer in `NOTES.md`.

**Hints.** Take `out` as `const py::object&`, check `py::isinstance<py::array>`, then
`out.dtype().is(py::dtype::of<double>())`, `out.flags() & py::array::c_style` and
`out.writeable()`. Release the GIL with `py::gil_scoped_release` after the last call into Python
and the last exception raised.
