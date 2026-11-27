# Exercise 23.5 (A): Audit an agent's loss counter

**Goal.** An agent finished the loss counter of a readout link: the numbers an operator reads
to judge whether a scan is complete. Its six tests pass, and it says no edge case is left.
Check that every counter means what the specification says, for everything this chapter says a
network and a link do to datagrams, and write the tests that prove your answer.

**Time.** 1 hour.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `loss_counter.hpp` (`before/` holds the file before it).

The code under audit is `tests/subject.hpp`, which includes the agent's version or the
corrected one according to `EX_MUTANT`.

**What you write.**
- `starter/test_audit.cpp`: GoogleTest tests of `ex235::LossCounter`, one per thing the
  network or the link can do.
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test
  that shows it, what the operator would read, and the correction.

**Acceptance** (`ctest --test-dir build/mine -L starter -R ch23/audit`):
- `original`: your tests pass on the corrected change;
- `mutant_1`: they fail on the agent's change;
- `mutant_2`, `mutant_3`: they fail on each defect of the change on its own.

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** What does `static_cast<std::int32_t>` give for a distance of exactly 2^31, in both
directions? A link both delays and duplicates a packet: count it through `{1, 3, 2, 4, 2}`.
