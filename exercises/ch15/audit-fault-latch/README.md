# Exercise 15.6 (A): Audit a risk control an agent implemented

**Goal.** An agent extended a board's fault latch to implement risk control RC-27 of hazard
H-10, and proposes its five passing tests as the control's verification in the risk file.
Decide whether the control reduces the risk it cites: for each cause the control names, does
the code latch, and does the operator read the truth? Write the tests that prove your answer.

**Time.** 1 hour.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `fault_latch.hpp` (`before/` holds the file before it).

The code under audit is `tests/subject.hpp`, which includes the agent's version or the
corrected one according to `EX_MUTANT`.

**What you write.**
- `starter/test_audit.cpp`: GoogleTest tests of `ex156::FaultLatch`, one for each cause the
  control names and for what the operator reads.
- `starter/REPORT.md`: each defect, the part of RC-27 it leaves undone, the test that shows
  it, the hazardous situation it leaves open, and the correction. End with your verdict on the
  agent's claim that the tests verify the control.

**Acceptance** (`ctest --test-dir build/mine -L starter -R ch15/audit`):
- `original`: your tests pass on the corrected change;
- `mutant_1`: they fail on the agent's change;
- `mutant_2`, `mutant_3`: they fail on each defect of the change on its own.

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** A cycle has reads and writes. Trace the counter through cycles whose reads all
succeed and whose write fails. Then read the message the operator gets when the board trips
on its own at a reading of 120 uA.
