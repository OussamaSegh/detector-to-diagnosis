# Exercise 34.1: notes

The starter fails four of the five tests: it lists every pair twice (as (a, b) and (b, a)), keeps
pairs below `min_shared`, counts a commit of 21 files, and so also gets the degrees wrong.

Design choices:

- A file's commits are counted only over the commits that are kept. Counting the mass commit in
  a file's total but not in its pairs would lower every degree of the files it touched.
- `sorted(set(files))` before the pairs: a file listed twice in one commit (it does not happen
  with `--name-only`, but a hand-made log may do it) must not pair with itself.

By hand:

1. On MiniDAQ's history at Chapter 34 (`-- minidaq/`), the top pair is the two CMake files
   (`minidaq/CMakeLists.txt` and `minidaq/tests/CMakeLists.txt`, 20 commits, degree 1.0): every
   new source comes with its test. Next come the expected pairs, a header and its source
   (`acquisition_pipeline.hpp` and `.cpp`) and a source and its test (`acquisition_config.cpp`
   and `test_config.cpp`). The pairs worth a question cross items: `acquisition_config.hpp` and
   `acquisition_service.cpp` (4 commits, degree 1.0), and `control/ports.hpp` with the same
   service: every change to the configuration's interface has also changed the service. That is
   a dependency the architecture description should state, and a reviewer of a configuration
   change should look for its other half.
2. With the smaller count, a degree of 1.0 says "every time the less often changed file changed,
   the other did too": a strong statement about the smaller file. With the larger count the
   degree is small whenever one file is busy for other reasons, which hides the dependency.
3. A single developer who works on both at the same time (a habit, not a dependency), and a
   process rule that makes them change together (a version number, a CHANGELOG, a generated
   file that is committed).
