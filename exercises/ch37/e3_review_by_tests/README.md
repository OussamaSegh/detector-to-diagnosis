# Exercise 37.3 (H): A review written as tests

**Goal.** Review a function an AI assistant wrote by testing it against its requirement, not
against its own code. The function in `tests/subject.hpp` reads well, compiles without a warning
and passes the two tests the assistant wrote with it. Seven other versions, each as fluent, pass
those tests too and are wrong. Your tests must catch all seven and pass on the right one.

**Time.** 3 hours.

**The requirement** (SRS-EX-037, for this exercise):

> The coincidence check shall report two singles as coincident when (1) both timestamps are valid
> values of the 40-bit picosecond counter, from 0 to 2^40 - 1, and (2) their distance, taken the
> shorter way around the counter's circle of 2^40 picoseconds and independent of their order, is
> (3) at most the window, and (4) the window is less than half the circle (2^39 picoseconds); in
> every other case it shall report them as not coincident.

**What to write.** Tests in `test_review.cpp` (GoogleTest), at least 8, from the requirement:
one or more per clause, with the values at the edge of each.

**Starter.** `starter/test_review.cpp` holds the assistant's two tests: a pair 2 ns apart in a 4 ns
window, and a pair 10 ns apart.

**Acceptance.** CTest builds your tests against the function and against each of the seven
mutants: `.../original` must pass, every `.../mutant_N` must fail (your tests catch it), and
`.../at_least_8_tests` must pass.

**Then, by hand.**
1. For each mutant, which clause of the requirement does it break, and what would it do in a
   scanner? Which would a reader of the code notice?
2. Why are the assistant's own tests no evidence for its code?
3. Which of your tests would you have written without the requirement in front of you?
