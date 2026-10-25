# Exercise 16.1 (E): Map MiniDAQ's documents to ISO 13485

**Goal.** Map each MiniDAQ document to the clause of ISO 13485 it is evidence for, and write the
checker that finds the gaps and the usual mistakes of such a map.

**Time.** 45 minutes.

**Starter.** `starter/clause_map.py` only checks that the documents exist in the list.
`starter/mapping.json` is a first draft with three clauses and one classic mistake.

**Acceptance** (`tests/test_clause_map.py`, run by CTest as `ch16/e1_clause_map/<variant>/unittest`):
- `problems()` reports an unknown clause or document, a missing design and development clause
  (7.3.2 to 7.3.10), one with neither evidence nor a plan, a document no clause uses, and
  verification evidence listed as validation.
- `mapping.json` has no problems, puts the SRS under inputs, the trace matrix under verification,
  the SOUP list under purchasing and the risk file under 7.1, and gives validation a plan of at
  least eight words instead of evidence.

Then answer in `NOTES.md`: an auditor asks for MiniDAQ's design validation. What do you show, and
what do you say?

**Hints.** The clause topics are in `tests/clauses.json` in this book's words. MiniDAQ's own index
is `docs/regulatory/qms/design-file.json`; try the exercise before you read it.
