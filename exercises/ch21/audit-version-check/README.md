# Exercise 21.6 (A): Audit an agent's version rules

**Goal.** An agent implemented the rules that keep VERSION honest, the version every crash
report names. Its five tests pass, and it says its rule is more robust than the
specification's. Decide whether the version a crash report names can still send an
investigator to the wrong code, and write the tests that prove your answer.

**Time.** 45 minutes.

**What you get** (in `change/`):
- `SPEC.md`, the task as the agent was given it;
- `TRANSCRIPT.md`, the session, condensed;
- `agent.patch`, the agent's diff of `version_rules.py` (`before/` holds the file before it).

The code as the agent left it is `tests/agent/version_rules.py`.

**What you write.**
- `starter/audit.py`: tests in the class `Audit`, which reach the code under audit as
  `self.subject` (`self.subject.problems(...)`).
- `starter/REPORT.md`: each defect, the rule it breaks, the test that shows it, what an
  investigator would do with a crash report it lets through, and the correction.

**Acceptance** (`tests/test_audit.py`, run by `ctest --test-dir build/mine -L starter -R ch21/audit`):
- your tests pass on the corrected change (`tests/reference/`);
- they fail on the agent's change (`tests/agent/`);
- they fail on each defect of the change on its own (`tests/defects/`).

Do not open `tests/reference/` or `tests/defects/` before your report is written: they are
the answer. The defects are taken from MiniDAQ's own problem reports; the solution names them.

**Hints.** Walk one release through its commits: the last -dev commit, the release commit, the
tag-list commit, a forgotten bump, the next chapter. Which of them does "the newest release on
any commit" accept? And what does Python's `$` match, besides the end of the text?
