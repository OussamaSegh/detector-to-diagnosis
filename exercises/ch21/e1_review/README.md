# Exercise 21.1 (M): Review a change with the checklist

**Goal.** Review a proposed change the way Chapter 21 teaches: with the
[code review checklist](../../../docs/code-review-checklist.md), section by section, and with
findings written as its section 7 says. The change adds a rate meter for the readout link. It
compiles, its unit test passes, and it has defects of the kinds that only a reader finds:
concurrency, a boundary, a lifetime, an error path, an initial state, and a test that proves
little.

**Time.** 45 minutes.

**Starter.** `starter/findings.py`, an empty list of findings. The change is
`tests/change.diff`, with the author's description at the top.

**Tasks.**
1. Read the description, then the header, then the source, then the test. For each section of
   the checklist, note what you checked.
2. Write each finding as a dict: the line of `change.diff` it points at (counted from 1), a
   severity (`blocker`, `major`, `minor` or `question`), a category, and a text that says what
   you observed and why it matters. Say what is wrong, not how you would rewrite it.

**Acceptance** (`ch21/e1_review/<variant>/unittest`): every finding is well formed; each of the
three blockers seeded in the diff is found and called a blocker or major; at least five of the
six seeded defects are found; at most two blocker or major findings point at no seeded defect.
The seeded defects are listed in `tests/test_review.py`, so do the review before you read it.

Then answer in `NOTES.md`: which section of the checklist found the most serious defect, and
why would the unit test never have found it?
