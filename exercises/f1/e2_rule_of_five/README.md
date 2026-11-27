# Exercise F1.2 (M): A rule-of-five buffer with a counting test

**Goal.** `Samples` owns a `new[]` array of doubles. The starter declares a destructor and nothing
else, so the compiler-generated copies share one array, and two destructors free it twice. Write
the copy constructor, the copy assignment, the move constructor and the move assignment, so that
copies are deep, moves steal and every array is freed exactly once.

**Time.** 60 minutes.

**Acceptance tests** (`tests/test_samples.cpp`). The class counts its allocations, and the tests
check the counts:
- a copy allocates exactly once and is independent of the original;
- copy assignment is deep and survives `b = b`;
- a move allocates nothing and leaves the source empty;
- the moves are `noexcept`, so a growing `std::vector<Samples>` moves its elements instead of
  copying them;
- after any mix of copies and moves, no array is left allocated.

Under the `asan-ubsan` preset the starter stops at the first double free.

**Hint.** Write the copy constructor by delegating to `Samples{n}`, the copy assignment as copy and
swap, and the moves with `std::exchange`. Then read `NOTES.md` on why production code prefers the
rule of zero.
