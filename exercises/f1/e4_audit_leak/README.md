# Exercise F1.4 (A): A class that leaks on an exception

**Goal.** Audit the recorded change in `CHANGE.md`: a coding assistant added `RunLog` and said
"the destructor deletes both, so there is no leak". Find what is wrong before you run anything,
write your findings in `REVIEW.md` (each finding: what, where, the input that shows it, the
fix), then fix `starter/run_log.hpp` until the acceptance tests pass.

**Time.** 45 minutes.

**Acceptance tests** (`tests/test_run_log.cpp`):
- the normal path frees the header and the index;
- a capacity of 0 throws `std::invalid_argument` **and** leaks nothing;
- copies are independent and freed once; moves leave no second owner.

The starter, the change as recorded, fails the last three. Under the `asan-ubsan` preset it also
reports a double free and a leak.

**What to look for.** Two findings are enough to reject the change. The transcript's claim is about
the destructor; ask when the destructor does not run. Then ask what the compiler-written copy does
with two raw pointers.
