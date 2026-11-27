# Exercise 7.6 (A): Audit an agent's change to a reader of untrusted input

**Goal.** An agent added a floating-point setting and a second schema version to the
acquisition settings reader. Its change passes the five tests it wrote, and it says the reader
still never throws. Find out whether that is true, with this chapter's view of input that you
did not choose, and write the tests that prove your answer.

**Time.** 1 hour.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `settings.hpp` (`before/` holds the file before it).

The code under audit is `tests/subject.hpp`, which includes the agent's version or the
corrected one according to `EX_MUTANT`.

**What you write.**
- `starter/test_audit.cpp`: GoogleTest tests of `ex76::read_settings`, written from the
  specification and from what a fuzzer would send.
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test
  that shows it, its effect at the scanner, and the correction.

**Acceptance** (`ctest --test-dir build/mine -L starter -R ch07/audit`):
- `original`: your tests pass on the corrected change;
- `mutant_1`: they fail on the agent's change;
- `mutant_2`, `mutant_3`: they fail on each defect of the change on its own.

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** Which exceptions can `std::stod` throw, and which one does the agent catch? What
is the difference, for the version check, between a key that is missing and a value that is
empty? A short run of `fuzz_config`'s idea, by hand: the largest and smallest numbers you can
write.
