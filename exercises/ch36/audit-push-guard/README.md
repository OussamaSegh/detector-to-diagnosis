# Exercise 36.5 (A): Audit an agent's push guard

**Goal.** An agent wrote the guard that stops another agent from rewriting published history:
it refuses a `git push` that forces, deletes, or reaches a branch the session does not own. Its
eight tests pass, and it says the guard covers every form. Check that against git's own syntax,
and write the tests that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `push_guard.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/push_guard.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.refusals(command, own_branch)`).
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the command
  that gets through, what it does to the repository, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch36/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** Read the `<refspec>` section of `git help push`: what does a refspec with an empty
source do? And how does git read `-fu`?
