# Chapter 1: the cost of a throw, and of a ranges pipeline

`costs.cpp` measures the two costs Chapter 1 quotes: a throw and catch through 2, 11 and 51
frames (the `Frames` column counts the calls below the first), each frame with a destructor,
against returning the same error as a `std::expected`; and an energy filter over 1,000,000
singles written as a loop and as `filter | transform` views. `run.sh` builds it with `-O2` and
C++23 and writes `costs.txt`, the median of 11 repetitions of each:

    measurements/ch01/run.sh g++

The first version had frames without a destructor, and GCC folded the recursion into a loop: the
no-error path through 50 frames took 0.6 ns and the throw cost did not depend on the depth. A
frame with a destructor, as real code has, keeps the frames and makes unwinding run it.

With it, a throw costs 2 to 34 µs, growing with the depth, and a returned error 2 to 142 ns. The
chapter's sentence that one throw in a thousand singles would dominate the budget was written
before the measurement; at 11 frames it is a quarter of it (8 ns of 33), and the text now says
so. The views ran within 6% of the loop (5.1 against 4.9 ns per single).
