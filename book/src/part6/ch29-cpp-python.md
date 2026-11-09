# C++ and Python: the projector behind a binding {#ch29}

::: box-why
The physicists write their algorithms in Python, and they should: the corrections, the
reconstruction loop, the analysis and the plots change every week, and NumPy makes them short and
readable. The loops that take the time are few, and they are where C++ earns its place. Moving
one of them across the language boundary is a small piece of code and a large responsibility.
The boundary is where a Python array with the wrong shape or the wrong memory layout becomes a
C++ pointer that reads the wrong numbers, where an exception must become an error the caller can
handle, and where two implementations of the same algorithm start to drift apart. This chapter
moves the projector of Chapter 28 into a C++ library, calls it from Python through pybind11, and
runs one set of tests on both sides. You will see a first C++ version that was no faster than
NumPy, an array that the boundary would have read transposed, and a test that passed with a data
race in it.
:::

**A day in the life.** A research group simulates a scan of a digital phantom, drawn from a CT,
with the clinical projector, which is C code called from Python through `ctypes`. The
reconstruction shows the hot rod below the center of the image, where the phantom has it to the
right of the center. The reconstruction is checked, the geometry is checked, and both are right.
The cause is one line in the script that made the phantom: its image had been transposed with
`.T` to match the CT's axes, which in NumPy changes how an array is read, not where its numbers
are in memory. The C code read the memory as rows, so it projected the transpose of the phantom
the script showed. Nothing failed: the simulated data were consistent, and the reconstruction
converged to a perfectly plausible image, mirrored on the diagonal. The fix is at the boundary.
The binding now accepts any layout and converts it, or refuses what it cannot read, and a test
passes a transposed array and compares the result with a contiguous one.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Decide which part of a Python program to move into C++, from a measurement rather than a
   guess.
2. Write a C++ library with an interface that a binding can call safely, and test it on its own.
3. Expose it to Python with pybind11: arrays with a declared dtype and layout, checked shapes,
   exceptions that become Python errors, and the GIL released while C++ computes.
4. Share a loop between threads without losing work or racing on the output, and keep the result
   reproducible.
5. Run the same tests on two implementations of one algorithm, and compare them with a tolerance
   you can justify.
6. Build the module with CMake and a pinned dependency, and record it as SOUP and as a tool.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (threads and data races), Chapter 7 (static analysis and sanitizers), Chapter 28 (the
projector and OSEM). You need the Python headers (`python3-dev`) and NumPy. Reading: about 2.5
hours. Exercises: 3 hours. Milestone: 5 hours. If time is short, do Exercises 29.1 and 29.3.

## What moves, and what stays

Measure first. In Chapter 28's reconstruction almost all of the time is in two functions: the
forward projection and the backprojection. Everything else, the ratio of counts, the update, the
subsets, the corrections, is a few array operations per subset. The numpy projector takes 57 ms
for a forward and 49 ms for a backprojection of MiniDAQ's 2D sinogram on the reference machine,
and keeps 89 MB of weights for a 128 x 128 image (`measurements/ch29/projector.txt`). A 3D
reconstruction has the oblique planes as well, many times as many lines, and its weights would
not fit in memory.

So the projector moves, and only the projector. The algorithm stays in Python, where the
physicists read it, change it and test it. The numpy projector stays too, as the reference: the
C++ one must give the same numbers, and a test says so on every build (ADR 0024).

There are several ways to call C++ from Python. `ctypes` and `cffi` call a C function with raw
pointers and lengths; every check of shape, dtype and layout is then written by hand on the
Python side, where nothing enforces it. Cython is a language of its own. Numba compiles Python
loops at run time. pybind11 and its smaller successor nanobind generate the conversions between
Python objects and C++ types from C++ declarations. MiniDAQ uses pybind11 3.1.0, pinned by
commit like every other dependency, because it lets the C++ side declare what it accepts and
checks it for every caller.

## The C++ library

### An interface a binding can call

The library, `recon/`, is plain C++20 with no Python in it. Its interface takes spans and sizes,
throws standard exceptions for anything that does not fit, and says what it guarantees about
threads:

```{.cpp include="recon/include/recon/joseph.hpp" snippet="api"}
```

Keeping Python out of the library has three advantages. It can be tested with GoogleTest like
the rest of MiniDAQ, under the sanitizers. It can be called from a C++ program, a future
reconstruction server, without a Python interpreter. And the binding stays a thin layer that does
one job: checking and converting.

### Weights on the fly

The numpy projector precomputes its weights because NumPy is fast only on whole arrays. C++ has
no such constraint, and computes each line's weights as it walks along it, so the projector
keeps nothing but the lines:

```{.cpp include="recon/src/joseph.cpp" snippet="walk"}
```

`walk` is a template that calls `visit(pixel, weight)` for every pixel of a line: forward
gathers with it, back scatters with it, and because both call the same function with the same
arguments, back is the adjoint of forward by construction. It decides whether to step along
columns or rows once per view, from the mean direction of the view's lines, exactly as the numpy
projector does; with that decided per line instead, the two would differ for the lines of a view
near 45 degrees.

### Threads

The lines are independent, so the forward projection gives each thread a contiguous chunk of them
and each output value is written by exactly one thread. The backprojection is harder: every
pixel lies on many lines, so two threads adding into the same image would race on the same
element. Each thread adds into an image of its own, and the images are summed in thread order:

```{.cpp include="recon/src/joseph.cpp" snippet="back"}
```

The cost is one image per thread, 0.5 MB for four threads at 128 x 128. The gain is that no
thread waits for another, there is no lock, and the result is the same in every run with the
same number of threads. Between thread counts it differs only by rounding, because floating-point
addition is not associative and the partial sums are added in a different grouping:
`TheThreadsDoNotChangeTheResult` requires bit-for-bit equality for the forward projection, equal
bits for repeated runs, and 1e-12 between one thread and four for the backprojection. Exercise
29.2 has you write both halves, and its starter has the two classic mistakes: chunks of
`count / threads` that lose the remainder, and threads that share one output. The first fails
the test every time. The second fails it on some runs only; ThreadSanitizer reports it on every
run, which is why CI runs the library's tests under the `tsan` preset.

Figure [](#fig-ch29-threads) shows both schemes.

```{.figure #fig-ch29-threads src="book/figures/tikz/ch29/threads.tex" caption="Threads in the projector. The forward projection gives each thread a contiguous chunk of lines; the backprojection gives each thread an image of its own and sums the images in thread order." alt="Left, a bar split into four chunks for threads 0 to 3, with the chunk bounds k times count over threads, so no remainder is lost and each output has one writer. Right, four small images for threads 0 to 3 summed into one, with no lock and the same bits for the same thread count." width="85%"}
```

### Tests in C++

`recon/tests/test_joseph.cpp` tests the library on a geometry small enough to know the answers:
the dot-product test, the chords of a disc, the sinusoid of an off-center point, the threads, a
subset as the rows of its views, and the refusal of every input that does not fit the geometry.
They run in every preset, including the sanitizers, where the Python module is not built.

## The binding

### pybind11 in the build

pybind11 is fetched at a pinned commit, like GoogleTest:

```{.cmake include="cmake/Dependencies.cmake" from="if(MINIDAQ_BUILD_RECON_PYTHON)" to="=endif()"}
```

`pybind11_add_module(recon_cpp python/recon_cpp.cpp)` builds a shared object named for the
Python that will load it, `recon_cpp.cpython-313-x86_64-linux-gnu.so` on the reference machine.
A module built for one Python version does not load into another. The option
`MINIDAQ_BUILD_RECON_PYTHON` is on by default, and off in the sanitizer and fuzzing presets,
whose instrumented code would be loaded into an uninstrumented Python interpreter.

### Arrays at the boundary

A NumPy array is a block of memory with a dtype, a shape and strides: how many bytes to step for
the next element along each dimension. Two arrays with the same values can have different
strides. A C-ordered array has its rows one after the other; `a.T` and `np.asfortranarray(a)`
have their columns one after the other; `a[::2, ::3]` skips elements. Code that takes the data
pointer and indexes it as `row * cols + col` reads the right elements only from a C-ordered
array. That is the mistake of the day in the life, and the starter of Exercise 29.1.

Figure [](#fig-ch29-strides) shows the same six values in the two layouts.

```{.figure #fig-ch29-strides src="book/figures/tikz/ch29/strides.tex" caption="Two arrays with the same values and different strides. Indexing the data pointer as row times columns plus column reads the right element only from the C-ordered one." alt="A 2 by 3 array with values a to f. Below it, its memory in C order, a b c d e f, strides 24 and 8, where element 3 is d, right; and in Fortran order, a d b e c f, strides 8 and 16, where element 3 is e, wrong." width="80%"}
```

The module asks pybind11 for exactly what the C++ reads, and checks the rest itself:

```{.cpp include="recon/python/recon_cpp.cpp" snippet="check"}
```

The array type is `py::array_t<double, py::array::c_style | py::array::forcecast>`. With it,
pybind11 hands the function a C-contiguous float64 array: the caller's own, if it is one, or a
converted copy, if it is of another dtype or layout. The shape is checked before anything is
read, and the error names both the expected and the given shape, because the caller needs to know
which of their arrays was wrong. A list of views is converted to a vector and every view checked
against the geometry.

### Exceptions and the GIL

The C++ throws `std::invalid_argument` and `std::out_of_range`, and pybind11 translates them into
Python's `ValueError` and `IndexError`: a caller's mistake surfaces as an exception they can
catch and read, not as a crash of the interpreter. The forward projection then releases the GIL:

```{.cpp include="recon/python/recon_cpp.cpp" snippet="forward"}
```

The global interpreter lock lets one thread at a time run Python code. While the projector
computes, it holds no Python object and calls no Python function, so it releases the lock and
other Python threads can run, for example one that writes the previous image to disk. The arrays
it reads stay alive, because the call holds references to them. What the C++ may not do without
the lock is touch any Python object: create one, change one, raise a Python exception. The output
array is allocated before the lock is released and returned after it is taken back.

Figure [](#fig-ch29-boundary) follows one array across the boundary.

```{.figure #fig-ch29-boundary src="book/figures/tikz/ch29/boundary.tex" caption="The binding boundary. pybind11 hands the C++ a C-contiguous float64 array, converting a copy when it must; the module checks the shape, releases the GIL and computes without touching a Python object." alt="Left in a Python band, a NumPy array with dtype, shape and strides, then array_t with c_style and forcecast, which makes a converted copy for another dtype or layout. Right in a C++ band, check ndim and shape, release the GIL, project on threads without Python objects. An arrow back from the shape check says a wrong shape raises a ValueError naming both shapes." width="100%"}
```

## One set of tests for both sides

### The same interface

`tools/recon/project.py` wraps the module in a class with the numpy projector's interface:

```{.python include="tools/recon/project.py" snippet="cpp"}
```

OSEM, the measurements and the tests take either projector. `load_cpp` finds the module in the
directory that `MINIDAQ_RECON_CPP` names, which CTest sets to the build directory, so a test
never picks up a stale module from somewhere else on the path.

### The same tests

The tests that define the projector are the Python tests of Chapter 28: two angles per view, the
adjoint, the chords, the sinusoid, the likelihood, noiseless data, unmeasured bins, the subsets.
`tools/test_recon_cpp.py` runs them again with the C++ projector:

```{.python include="tools/test_recon_cpp.py" snippet="same-tests"}
```

Each test class of `test_recon.py` builds its projector with `cls.make`, the numpy `Projector` by
default; the subclasses replace it, and unittest runs every inherited test on the C++ projector.
A requirement verified on one implementation is now verified on both, with the same code.

Figure [](#fig-ch29-tests) shows how the three kinds of tests fit together.

```{.figure #fig-ch29-tests src="book/figures/tikz/ch29/tests.tex" caption="One set of tests for both sides. Chapter 28's tests run on each projector, a comparison on random data holds them to the same numbers, and the C++ library has tests of its own under the sanitizers." alt="Chapter 28's projector tests at the top, with arrows to the numpy Projector, the reference, and the CppProjector of the recon_cpp module. A double arrow between them is the comparison on random data with differences of 4.1e-08 forward, 4.9e-09 back and 1.0e-08 for an OSEM image. C++ tests under ASan, UBSan and TSan point to the C++ projector." width="75%"}
```

### The same numbers

The tests prove each projector right on its own. A third set proves them equal: the forward and
back projections of a random image and a random sinogram on MiniDAQ's geometry, compared line by
line, and an OSEM image reconstructed with each.

| Quantity | Largest difference, relative to the largest value |
|---|---:|
| forward, random image | 4.1e-08 |
| back, random sinogram | 4.9e-09 |
| back, 1 thread against 4 | 2.5e-15 |
| OSEM image, 4 iterations of 8 subsets | 1.0e-08 |

: The C++ projector against the numpy projector (`measurements/ch29/projector.txt`, section 1).

The differences come from the numpy projector, which keeps its weights in float32, about seven
significant digits; the C++ one computes them in double. The test's tolerance is 1e-6 relative to
the largest value: 25 times the largest difference found, and far below the smallest real
mistake, such as an angle half a view off, which changes the projection by more than 10%. Random
data matters as much as the tolerance. A centered disc projects to the same profile in every view
and symmetrically in s, so a comparison on a disc cannot see a wrong angle or a reversed sign;
Exercise 29.3's starter compares on a disc and accepts both.

The boundary has tests of its own: arrays of the wrong shape and views that do not exist are
refused with the shapes in the message; a Fortran-ordered, a transposed, a strided and an int32
array give bit for bit what a C-ordered float64 one gives; the inputs are left unchanged and the
outputs are new arrays.

## Is it faster?

| Projector | Forward | Back |
|---|---:|---:|
| numpy | 57.1 ms | 48.9 ms |
| C++, 1 thread | 33.8 ms | 35.7 ms |
| C++, 2 threads | 20.8 ms | 27.0 ms |
| C++, 4 threads | 14.4 ms | 15.0 ms |

: One projection of MiniDAQ's 2D sinogram, 128 x 128 pixels, median of 7 runs on the reference
machine with 4 CPUs (`measurements/ch29/projector.txt`, section 2).

Four iterations of 8 subsets take 0.18 s with the C++ projector on 4 threads and 1.17 s with
numpy. The C++ projector keeps no weights, so the 89 MB are gone too, and the 0.3 to 0.6 s the
numpy one spends computing them.

The first C++ version was not faster. On one thread it took 66 ms for a forward projection, where
numpy took 62 (`measurements/ch29/first-version.txt`). NumPy's loop over precomputed weights is
already compiled code, and the first C++ version computed each step's position with two
divisions. The position across the line is linear in the step, `f_k = f_0 + k df`, and
computing it that way halved the time. The lesson is the order of the work: the move to C++ made
the threads and the memory possible, and a measurement found the arithmetic that mattered. A
claim that C++ is faster is a measurement, not a property of the language.

Figure [](#fig-ch29-speed) puts both versions side by side.

```{.figure #fig-ch29-speed src="book/figures/plots/ch29/speed.py" caption="One projection of MiniDAQ's 2D sinogram, numpy against the C++ projector on 1, 2 and 4 threads. The first C++ version (grey) was slower than numpy on one thread; computing the position as f_0 + k df made it faster." alt="Two panels of horizontal bars, forward and back projection, in milliseconds. Current: numpy 57 and 49, C++ one thread 34 and 36, two threads 21 and 27, four threads 14 and 15. First C++ version in grey: one thread 66 and 66, two threads 34 and 39, four threads 21 and 24." width="100%" inputs="measurements/ch29/projector.txt measurements/ch29/first-version.txt"}
```

## What the boundary costs

Two implementations of one algorithm must be kept the same. Every change is made in both, or
the numpy one is retired by a decision that makes the C++ one the reference; until then the
comparison test is the contract. The build needs the Python headers and pybind11, and a module
built for one Python version does not load into another, so the module is built for the Python
of the machine that runs the reconstruction. The sanitizer builds test the library, not the
module, and the module's own checks are tested from Python.

::: box-regulated
- **pybind11 is SOUP.** It is pinned by commit in `cmake/Dependencies.cmake`, listed in section 2
  of the SOUP list (version 11) and in the SBOM's known dependencies, and recorded as a tool of
  class T3 (TL-32): the conversions it generates sit between the physicists' arrays and the
  projector of every image. The boundary tests are the evidence that its conversions do what the
  binding declares.
- **A second implementation is a change to the tool.** TL-31 now names both projectors, its
  evidence includes the comparison and the C++ tests, and H-13 gains a cause and a control
  (RC-43): the two implementations differ, an array is read in the wrong layout, or lines are lost
  between threads.
- **Requirements for a boundary.** SRS-REC-004 to SRS-REC-006 state what can be checked: the same
  numbers as the reference, the refusal and conversion of arrays, the independence from the
  number of threads.
- **The reference is a decision.** Which implementation defines the right answer, and when that
  changes, belongs in an ADR and a change request, not in a commit message (assumption: confirm
  with team how your organization records a change of reference implementation).
:::

::: box-mistakes
- **Indexing the data pointer of any array.** Only a C-ordered array has its rows in a row. Ask
  for `c_style | forcecast`, or index with strides.
- **Reading `shape(1)` before checking `ndim()`.** The error is about your code, not the call.
- **Writing into the caller's array.** It changes some callers' data and not others', depending
  on whether pybind11 had to copy.
- **Touching Python objects without the GIL.** Allocate before releasing it, return after taking
  it back.
- **Chunks of `count / threads`.** The remainder is lost. Use `count * k / threads`.
- **Threads sharing one output.** A data race that passes most test runs. Give each thread its own
  and run the tests under ThreadSanitizer.
- **Comparing two implementations on a symmetric object.** A centered disc cannot see an angle or
  a sign. Use random data, both directions, and a tolerance from the precision you expect.
- **Assuming C++ is faster.** The first version was not. Measure.
:::

::: box-askteam
1. Which parts of the reconstruction are in C++ or on a GPU, and which in Python? Who decided,
   from which measurements?
2. Which implementation is the reference, and how are the others compared with it?
3. How do the bindings check arrays: shape, dtype, layout? What happens to a Fortran-ordered
   array?
4. Which Python versions is the module built for, and how is it delivered to the machines that
   run it?
5. Do the C++ parts run under the sanitizers in CI? Are the threads tested for reproducibility?
6. Is the binding library on the SOUP list, and who reviews its updates?
:::

## Exercises {.unnumbered}

**Exercise 29.1 (M): A Python boundary that checks what it is given.** *Goal:* write a C++
function that Python calls through pybind11, and make the boundary safe for any array a caller
passes. *Starter:* `exercises/ch29/e1_boundary/starter/rows.cpp`, built into the module `rows`.
*Acceptance:* `tests/test_rows.py` passes: rows scaled correctly for C-ordered, Fortran-ordered,
strided and int32 arrays, wrong shapes refused with `ValueError` naming them, and the caller's
array left unchanged. Then answer in `NOTES.md` what the starter returned for a Fortran-ordered
array, why the int32 test passed with it, and what C++ may not do without the GIL. *Time:* 60
minutes.

**Exercise 29.2 (M): Work shared between threads.** *Goal:* share a loop between threads so that
every index is processed exactly once, and add many contributions into one output from several
threads without a data race and with a reproducible result. *Starter:*
`exercises/ch29/e2_threads/starter/`. *Acceptance:* `tests/test_parallel.cpp` passes: every index
covered once for counts from 0 to 43,584 and 0 to 9 threads, the serial sum to 1e-12 with 2 to 8
threads, the same bits in repeated runs, and an index outside the output refused. Then answer in
`NOTES.md` which indices the starter missed, what ThreadSanitizer reports for it, and why the last
bits may differ between thread counts. *Time:* 60 minutes.

**Exercise 29.3 (S): Is the second implementation the same?** *Goal:* write the check that a
second implementation of a projector does what the reference does. *Starter:*
`exercises/ch29/e3_equivalence/starter/equivalence.py`. *Acceptance:* `tests/test_equivalence.py`
passes: the same projector and a float32 one accepted, and angles half a view off, `s` reversed, a
backprojector that is not the adjoint, a scale error of 1e-4 and another geometry refused, each
with the reason in the message. Then answer in `NOTES.md` what the starter accepted, how to choose
the tolerance, and why the candidate's own dot-product test is needed. *Time:* 45 minutes.

## MiniDAQ milestone: the projector in C++ {.unnumbered}

::: box-milestone
**Goal.** The reconstruction runs with a C++ projector called from Python, which passes the
numpy projector's tests, agrees with it line by line, refuses and converts arrays at the boundary,
and is measured. **Start:** tag `ch28`. **End:** tag `ch29`.
:::

1. Write change request CR-0015 and ADR 0024; add SRS-REC-004 to SRS-REC-006 (SRS version 18),
   RC-43 under H-13, pybind11 to the SOUP list (version 11), the SBOM's known dependencies and the
   tool list (TL-32), and extend TL-31; update the architecture description (version 15).
2. Add `recon/` with `recon::JosephProjector` and its GoogleTest tests; add it to the static
   analysis.
3. Fetch pybind11, add the option `MINIDAQ_BUILD_RECON_PYTHON` and the module `recon_cpp`;
   install `python3-dev` in CI.
4. Add `project.CppProjector`, `tools/test_recon_cpp.py` and the test `tools.recon_cpp`.
5. Add `measurements/ch29/projector.py` and Exercises 29.1 to 29.3, with the CMake function
   `minidaq_pybind_exercise`.

**Definition of done.** `ci/run_all.sh` is green on all six presets, the library's tests pass
under ThreadSanitizer, and static analysis reports nothing; the trace matrix shows SRS-REC-004 to
SRS-REC-006 verified; the C++ projector agrees with the numpy one to 1e-6 and is faster on four
threads; every starter of the chapter fails. Tag `ch29`.

## Check yourself {.unnumbered}

1. Why does the projector move to C++ and the OSEM loop stay in Python?
2. Name three ways to call C++ from Python, and what each leaves to the caller.
3. Why does the C++ library contain no Python?
4. Why is the C++ backprojection the adjoint of its forward projection by construction?
5. What are an array's strides, and which arrays can be indexed as `row * cols + col`?
6. What does `py::array_t<double, py::array::c_style | py::array::forcecast>` give the function?
7. What may C++ code do, and not do, with the GIL released?
8. How does the backprojection avoid a data race, and what does it cost?
9. Why may the backprojection differ in the last bits between one thread and four?
10. A test of the threads passes ten times in a row. Is the code free of data races?
11. How does `test_recon_cpp.py` run the numpy projector's tests on the C++ projector?
12. How was the tolerance of 1e-6 chosen, and why relative to the largest value?
13. Why can a comparison on a centered disc not see a reversed `s`?
14. The first C++ version was no faster than NumPy. Why, and what made the second one faster?
15. What makes pybind11 SOUP, and which tool class does it have here?

## Summary {.unnumbered}

- Measure before moving code: the projector took nearly all of the reconstruction's time, so it
  moved, and the algorithm stayed in Python.
- `recon/` is a C++20 library with no Python, its own tests, and weights computed on the fly. Its
  forward and back call the same `walk`, so they are adjoint by construction.
- The threads share the lines; the backprojection adds into an image per thread and sums them in
  a fixed order: no race, no lock, reproducible bits for a given number of threads.
- The pybind11 module checks every array's shape, converts other dtypes and layouts with
  `c_style | forcecast`, translates C++ exceptions into Python ones, returns new arrays and
  releases the GIL while it computes.
- The numpy projector's tests run on the C++ projector, and the two agree to 4e-8 forward and
  5e-9 back; the tolerance is 1e-6, on random data.
- On one thread the first C++ version was as slow as NumPy; without the division per step it took
  34 ms against 57, and 14 ms on four threads. A reconstruction of 4 iterations of 8 subsets went
  from 1.17 s to 0.18 s.
- pybind11 3.1.0 is SOUP and tool TL-32; SRS-REC-004 to SRS-REC-006 and RC-43 cover the second
  implementation.

## Further reading {.unnumbered}

- The pybind11 documentation, <https://pybind11.readthedocs.io>: the chapters on NumPy arrays
  (`array_t`, its flags and `unchecked`), exception translation, and the GIL (verify: the version
  of the documentation that matches the pinned release).
- The NumPy documentation on the memory layout of arrays (strides, C and Fortran order) and on
  the C API, <https://numpy.org/doc/stable/>.
- The nanobind documentation, <https://nanobind.readthedocs.io>, for the alternative and its
  differences from pybind11 (verify: the current version's requirements).
- The Python documentation on extending and embedding the interpreter, and on the global
  interpreter lock, <https://docs.python.org/3/>.
- A. Williams, *C++ Concurrency in Action*, 2nd edition, Manning, 2019: sharing work between
  threads and the C++ memory model.
- The ThreadSanitizer documentation in the Clang manual, for what it reports and how.
- ADR 0024 and CR-0015 in the repository: the decision and the change record.
