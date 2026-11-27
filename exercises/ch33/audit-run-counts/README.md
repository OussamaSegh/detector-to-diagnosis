# Exercise 33.5 (A): Audit an agent's count checks

**Goal.** An agent wrote the two checks that make the end-to-end run's counts add up: the
singles recorded, and the sorter's partition of them. Its tests pass, and both checks pass on
the chapter's three runs. Decide whether a damaged run could pass them, or a good run fail
them, and write the tests that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `run_counts.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/run_counts.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject`.
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test that
  shows it, which runs it lets pass or makes fail, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch33/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** Count the sorter's counters in the specification, then the terms of the agent's sum.
"Passes on three runs" says what about a run with a single out of time order? Read the first
sentence of item 1 again, and look at the last time in `generated_ps`.
