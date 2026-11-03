# 0024. The projector in C++, called from Python through pybind11

Date: 2026-11-03
Status: Accepted

## Context

The reconstruction of Chapter 28 is numpy: 57 ms for a forward and 49 ms for a backprojection
of one 2D sinogram on the reference machine (measurements/ch29), and 89 MB of weights kept for a
128 x 128 image. A 3D reconstruction has the oblique planes too, many times the lines, and the
weights would not fit in memory. The physicists keep writing the algorithms, the corrections and
the analysis in Python; the projector is the loop that takes the time. Three questions:

- what moves to compiled code, and what stays in Python;
- how Python calls it;
- how the two implementations are kept the same.

## Options

1. **Stay in numpy**, vectorized further or with a JIT compiler such as Numba. No second language
   in the tool; a JIT is a large dependency of its own, and its speed depends on what it can
   compile.
2. **A C++ library called through ctypes or cffi.** No build-time dependency on Python's headers,
   but every array is passed as a raw pointer and a length, with the shape, dtype and layout
   checks written by hand on the Python side, where nothing enforces them.
3. **A C++ library with a pybind11 module.** The module converts NumPy arrays to C++ with a
   declared dtype and layout (copying when it must), turns C++ exceptions into Python ones, and
   lets the C++ release the GIL. A build-time dependency, header-only, and the Python headers.
4. **nanobind or Cython.** nanobind is pybind11's smaller, faster successor by the same author,
   with a narrower range of supported Python versions; Cython is a language of its own.

## Decision

Option 3, pybind11 3.1.0 pinned by commit (SOUP, tool TL-32), for the projector only.

- The projector is a C++20 library, `recon/` (`recon::JosephProjector`), with no Python in it and
  its own GoogleTest tests: the adjoint, the chords of a disc, the sinusoid, the threads, a
  subset, and what it refuses. Its weights are computed for every line on the fly, so it keeps
  only the lines.
- The module `recon_cpp` (`recon/python/recon_cpp.cpp`) checks every array's dimensions and
  shape, takes C-contiguous float64 (`c_style | forcecast`: another dtype or layout is
  converted, never reinterpreted), returns new arrays and releases the GIL while it computes
  (SRS-REC-005).
- `tools/recon/project.py` keeps the numpy projector as the reference and wraps the module in
  `CppProjector` with the same interface, so OSEM, the measurements and the tests take either.
  The tests of the numpy projector run on the C++ one, and the two are compared line by line
  (`tools/test_recon_cpp.py`, SRS-REC-004).
- The C++ shares the lines between threads; the backprojection adds into an image per thread and
  sums them in a fixed order, so it is reproducible for a given number of threads (SRS-REC-006).
- The module is built when `MINIDAQ_BUILD_RECON_PYTHON` is on, the default except with
  sanitizers and fuzzing, whose instrumented code would be loaded into an uninstrumented Python.
  The library and its C++ tests build in every preset, ThreadSanitizer included.

## Consequences

### Positive

- One projection takes 34 ms forward and 36 ms back on one thread, 14 and 15 ms on four, against
  57 and 49 ms in numpy, and keeps no weights; 4 iterations of 8 subsets take 0.18 s against
  1.17 s (measurements/ch29).
- The C++ is tested twice, by its own tests and by the Python tests that define the projector,
  and a mismatch between the two implementations fails a test, not an image.
- The boundary checks are written once, in C++, where every caller goes through them.

### Negative

- A second implementation of the same algorithm to keep the same: every change is made in both
  and compared (or the numpy one is retired, when the C++ one has become the reference by
  decision).
- A build that needs the Python headers (`python3-dev`) and pybind11, and a module that must be
  built for the Python version that loads it.
- The first C++ version was no faster than numpy on one thread (66 ms against 62 ms forward):
  numpy's loop over precomputed weights is already compiled code. Moving a loop to C++ is not a
  speed-up by itself; it was the division per step, removed, and the threads.
- The sanitizer builds test the library, not the module.
