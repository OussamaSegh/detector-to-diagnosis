# Exercise 18.1 (E): Fifteen tests for the timestamp rollover

**Goal.** Write at least fifteen unit tests of the time unwrapper, MiniDAQ's code that rebuilds
absolute time from the 38-bit time code that wraps every 1.374 s, so that every one of seven
plausible mistakes in it fails at least one of your tests.

**Time.** 60 minutes.

**Starter.** `starter/test_unwrap.cpp` has two tests and a list of behaviors they leave out. The
subject is `tests/subject.hpp`, a copy of `TimeUnwrapper` from
`minidaq/include/minidaq/format/packed_single.hpp` with seven seeded mistakes selected by
`EX_MUTANT`. Write your tests from the class comment and requirement SRS-FMT-012, not from the
mutants: the point is to learn what a test suite written from a specification misses.

**Acceptance** (run as `ch18/e1_unwrap_tests/<variant>/...`):
- `original`: every test passes on the real code (`EX_MUTANT=0`).
- `mutant_1` to `mutant_7`: each mutant fails at least one test (CTest expects these runs to
  fail).
- `at_least_15_tests`: fifteen test cases or more, each named for the behavior it checks.

Then answer in `NOTES.md`: which mutants survived your first attempt, and what kind of test
was missing for each?

**Hints.** Arrange, act, assert, and one behavior per test. What happens to the second word
after a wrap? What does `time_code - last_` compute when `time_code` is the smaller one?
