# Exercise 40.5 (A): Audit an agent's reader of an update store's state

**Goal.** An agent finished the reader of state.json, the file that tells a scanner's updater
which slot holds the good release and which is on trial. Its six tests pass, and it says every
malformed file gives `Damaged`. A field engineer may have edited the file by hand, years after
the release: decide what the updater does with every file it could find, and write the tests
that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `update_state.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/update_state.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.open_state(text)`, `self.subject.Damaged`).
- `starter/REPORT.md`: each defect, the sentence of the specification it breaks, the test that
  shows it, what happens at the scanner, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch40/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** "Lenient with hand-edited files": what is the trial slot after a person typed
`"trial": 7`? And what does `.get("good_version", "")` return when the key is there with a
number?
