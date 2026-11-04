# Exercise 34.3 (M): Pin down what legacy code does

**Goal.** Write characterization tests for a function nobody can explain: tests that record what
it does today, so that any change of its behavior, a mistake or a well-meant fix, fails a test
and becomes a decision instead of an accident. The technique is M. Feathers': before changing
code you do not understand, find out what it does by running it, and write that down as tests.

**Time.** 2 hours.

**The subject.** `tests/subject.hpp`: `legacy::corrected_rate(counts, live_us, real_us)`, the
live-time corrected count rate of a detector block from an older acquisition program. Its comment
is all the documentation there is. Read the code, not the mutants: `EX_MUTANT` selects one of seven
changes, and your tests are built against each.

**Starter.** `starter/test_characterize.cpp` has two tests of ordinary values. They pass on the
original and catch almost none of the changes.

**Acceptance** (run as `ch34/e3_characterize/<variant>/...`):
- `original`: every test passes on the function as it is.
- `mutant_1` to `mutant_7`: each change fails at least one test.
- `at_least_8_tests`: at least eight test cases.

**Then, by hand.**
1. Which of the seven changes would you call fixes, and which mistakes? Does the difference matter
   to the tests?
2. One of your tests pins a behavior that looks wrong (a dead block shows 0, not an error).
   Where would you record that it looks wrong, and who decides whether it changes?
3. Name each test after the behavior it pins, not after its numbers. Why does that matter more
   for characterization tests than for others?

**Hints.** Find the boundaries in the code: every comparison is a place where one more or one
less changes the answer. Try the values on both sides of each. Integer division truncates; find an
input where truncating and rounding differ, and one where the order of a multiplication and a
division matters.
