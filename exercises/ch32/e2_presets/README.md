# Exercise 32.2 (E): One command per configuration

**Goal.** Write the project's `CMakePresets.json` so that `cmake --workflow --preset dev` and
`cmake --workflow --preset asan` each configure, build and test the project, the same on a
laptop as in CI.

**Time.** 30 minutes.

**Starter.** `starter/CMakePresets.json` has two configure presets. The `asan` one compiles with
`-fsanitize=address` but does not link with it, and there are no build, test or workflow
presets. The library has a defect that no test sees: a loop reads one element past an array.

**Acceptance** (`tests/test_presets.py`, which runs each workflow in a copy of the project with
this build's compiler and generator):
- The `dev` workflow passes both tests.
- The `asan` workflow builds and then fails in its tests with AddressSanitizer's
  `heap-buffer-overflow` in `window.cpp`.
- Each configuration has a build, a test and a workflow preset of its name.

**Then, by hand.**
1. Fix the loop in `window.cpp` and run both workflows again. Which test found the defect?
2. Why does a read one past the end not make the `dev` tests fail?
3. Add a `CMakeUserPresets.json` with a preset of your own that inherits `dev`. Why does that file
   belong in `.gitignore`?

**Hints.** A workflow preset needs presets file version 6 (CMake 3.25). A sanitizer must be in the
link flags too: its runtime is a library.
