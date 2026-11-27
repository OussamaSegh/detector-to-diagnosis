# Exercise 8.6 (A): Audit an agent's coincidence finder

**Goal.** An agent was asked to add a coincidence finder to the Chapter 8 toolkit. Its change
passes the four tests it wrote, and it says the result is deterministic. Decide whether it is
right, with this chapter's physics as your oracle, and write the tests that prove your answer.

**Time.** 1 hour.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `pairs.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/pairs.py`. Read the patch and the specification
first.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.find_pairs(...)`, `self.subject.Single(...)`). Write them from
  the specification and the physics, not from the code.
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test that
  shows it, what it does to a scan, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch08/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`, one file per defect).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** How many pairs should 100 well separated annihilations give? Exercise 8.3 gives you
the number of chance pairs between two independent detectors: count them with `find_pairs`.
What does "whatever order the singles are given in" ask when two singles have the same time?
