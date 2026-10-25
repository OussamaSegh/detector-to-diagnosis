# Exercise 14.6 (E, extra): The known anomalies of a release

**Goal.** Generate the list of known residual anomalies that a release states, from the
problem reports, and refuse reports that nobody has evaluated.

**Time.** 45 minutes.

**Starter.** `starter/anomalies.py` checks the IDs, the required text fields and the status,
and renders every report, closed or open, in the order it finds them.

**Acceptance** (`tests/test_anomalies.py`, run by CTest as
`ch14/e6_known_anomalies/<variant>/unittest`):
- `problems()` reports a report without an evaluation, with `safety_relevant` that is not
  `true` or `false`, or with an empty rationale; an open report without a decision; a closed
  report without both its change and its verification; a duplicate or malformed ID.
- `render()` lists only the open reports, in ID order, each with its item, its relevance to
  safety, the reason and the decision, under a line that counts them and the safety-relevant
  ones.

Then answer in `NOTES.md`: MDQ-PR-005 says "relevant to safety: no". What evidence would make
you change that answer?

**Hints.** MiniDAQ's own reports are `docs/regulatory/problem-reports.json`; `tools/anomalies.py`
generates `docs/regulatory/known-anomalies.md` and the test `docs.anomalies` keeps it current.
