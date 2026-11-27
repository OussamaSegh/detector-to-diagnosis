# Exercise 30.5 (A): Audit an agent's reader of run metadata

**Goal.** An agent implemented what the daily QC report reads from a run's metadata. Its five
tests pass, and it says every failure ends in a clean message. The person who runs the report
every morning is a technologist, not a programmer: decide what they would see for every run
the report could be given, and write the tests that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `qc_metadata.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/qc_metadata.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.read_metadata(...)`, `self.subject.FormatError`).
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test that
  shows it, what the technologist sees, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch30/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** JSON has six kinds of value. Put each one in each place the reader looks. What are
`int("100000")`, `int(True)` and `int([1])` in Python?
