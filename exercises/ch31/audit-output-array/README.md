# Exercise 31.5 (A): Audit an agent's check of an output array

**Goal.** An agent wrote the check that decides whether a caller's NumPy array can take a
projector's output in place. Its six tests pass, and it says the check is exact. Decide which
arrays a scientist really passes, from files, other processes and other libraries, and whether
the check accepts each one it should; write the tests that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `out_array.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/out_array.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.writable_out(...)`).
- `starter/REPORT.md`: the defect, the sentence of the specification it breaks, the arrays it
  refuses, why the agent's tests could not see it, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch31/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`).

Do not open `tests/reference/` before your report is written: it is the answer. The defect is
taken from MiniDAQ's own problem reports; the solution names it.

**Hints.** Is it true that NumPy keeps one dtype object per type? Try `is` on the dtype of an
array that went through `pickle`, `np.load` or `newbyteorder()` twice. What do `==` and `is`
each compare?
