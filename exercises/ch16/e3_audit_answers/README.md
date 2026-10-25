# Exercise 16.3 (M): Answer an auditor's questions about the sorter

**Goal.** An auditor samples the coincidence sorter and asks ten questions. Answer each in a few
sentences, with the documents, records or tests that show it, and write the checker that reads
your answers the way the auditor will.

**Time.** 75 minutes.

**Starter.** `starter/audit.py` only checks that every question has an answer. The four answers
in `starter/answers.json` are what people say in their first audit.

**Acceptance** (`tests/test_audit.py`, run by CTest as `ch16/e3_audit_answers/<variant>/unittest`):
- `problems()` reports an unanswered question, an answer longer than 80 words, a hedge
  (`probably`, `should`, `I think` and the others in `HEDGES`, as whole words), an answer
  without evidence, evidence that is only directories, and evidence that does not exist: a
  file not in `tests/files.txt` or a test not in `tests/tests.txt` (both from tag `ch15`).
- `answers.json` answers all ten questions without problems, rests correctness on
  CoincidenceSorter.MatchesTheSimulatorsGroundTruth, names H-07 and the sorter's FMEA, points
  at ADR 0010 for the design, names the known anomaly MDQ-PR-007, and answers Q9 truthfully.

Then answer in `NOTES.md`: while you prepare Q9 you find that the answer is bad news. What do
you do before the audit, and what do you say in it?

**Hints.** Q9 needs `git log` on the sorter's two source files and section 5 of the SDP. Every
number in an answer must be one you can show: copy it from the record, do not remember it.
