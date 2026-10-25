# Exercise 18.3 (M): Branch coverage of the sinogram

**Goal.** Write unit tests of the sinogram histogrammer (`minidaq/src/processing/sinogram.cpp`,
Chapter 12) from its specification in `minidaq/include/minidaq/processing/sinogram.hpp`, until
your tests alone take at least 90% of the file's branches both ways. Then review every branch
that is still open: either reach it with another test, or accept it in `review.json` with a
reason a reviewer can check.

**Time.** 90 minutes.

**Starter.** `starter/test_sinogram_branches.cpp` has two tests, which take 41% of the branches;
`starter/review.json` accepts nothing.

**Acceptance.** This exercise measures coverage, so it is built only with the `coverage` preset
(Clang source-based coverage), with starters on:

    cmake --preset coverage -DMINIDAQ_BUILD_STARTERS=ON
    cmake --build --preset coverage --target ch18_e3_branch_coverage_starter
    ctest --test-dir build/coverage -R ch18/e3_branch_coverage/starter --output-on-failure

`tests/check_coverage.py` runs your tests alone and passes if they pass, reach at least 90% of
the branches of `sinogram.cpp`, and `review.json` accepts exactly the branches still open, each
with its line, column, the line's code as it is now, and a reason of at least six words. An entry
for a branch that is covered, or for a line that has changed, fails the check: a review is of
the code as it is.

Then answer in `NOTES.md`: which branches did the two starter tests leave open, what kind of test
was missing for most of them, and why is the branch you accepted not a gap?

**Hints.** Each `||` and `&&` is a branch of its own for each condition. Read what `locate()`
returns for each `Outcome`; then read which ends of a LOR are endpoints a and b, because the
time-of-flight bin depends on it. A `switch` whose cases cover the whole enumeration still has a
branch Clang counts.
