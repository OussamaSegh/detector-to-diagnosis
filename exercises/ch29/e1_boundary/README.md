# Exercise 29.1 (M): A Python boundary that checks what it is given

**Goal.** Write a C++ function that Python calls through pybind11, and make the boundary safe:
whatever array a Python caller passes, the C++ code either reads it correctly or refuses it with
an error that says why. This is what `recon/python/recon_cpp.cpp` does for the projector.

**Time.** 60 minutes.

**Starter.** `starter/rows.cpp` builds into the module `rows`. `scale_rows(a, factors)` should
return a new array `a[i, j] * factors[i]`. It takes `py::array_t<double>`, reads
`a.mutable_data()` as rows of `a.shape(1)` values, scales the rows in place and returns `a`.
Build it with `cmake -S . -B build/debug -DMINIDAQ_BUILD_STARTERS=ON` (the Python headers are
needed: `python3-dev`).

**Acceptance** (`tests/test_rows.py`, run by `ctest --test-dir build/debug -R ch29/e1`):
- A C-ordered float64 array is scaled row by row.
- A Fortran-ordered array, a strided view (`big[::2, ::3]`) and a transposed copy give the same
  answer as NumPy's `a * factors[:, None]`.
- An int32 array is converted and gives float64.
- A one-dimensional `a`, a `factors` of the wrong length and a two-dimensional `factors` raise
  `ValueError` with the shapes in the message.
- The caller's array is not changed, and the result does not share its memory.

**Then, by hand.**
1. What did the starter return for the Fortran-ordered array, and why did it not crash?
2. `py::array_t<double>` already converts an int32 array. Why did the int32 test pass with the
   starter while the float64 caller's array was changed?
3. The projector's binding releases the GIL around the computation. What may the C++ code not
   do while the GIL is released, and what would happen if the caller changed the array from
   another Python thread meanwhile? Answer in `NOTES.md`.

**Hints.** `py::array_t<double, py::array::c_style | py::array::forcecast>` gives you a
C-contiguous float64 array, converting (copying) any other. Check `ndim()` before `shape(1)`.
`unchecked<2>()` gives an accessor that indexes with the array's strides. Allocate the result
with `Array out({rows, cols})`.
