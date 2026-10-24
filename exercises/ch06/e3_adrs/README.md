# Exercise 6.3 (M): Write three ADRs, and a checker that keeps them honest

**Goal.** Record three of MiniDAQ's decisions as architecture decision records: the queue
between stages, the list-mode file format, and the control protocol. Then write a small
linter so that every future record has the same parts, because a template that nobody
checks decays within a year.

**Time.** 3 hours (about 45 minutes per record, 45 minutes for the linter).

**Tasks.**
1. Read `docs/adr/0001-record-architecture-decisions.md`: it defines the format (file name,
   title line, Date, Status, Context, Options with at least two entries, Decision,
   Consequences with Positive and Negative). The copy in `starter/adr/` is your 0001.
2. Write `0002` (queue between stages), `0003` (list-mode file format; "Proposed" is a
   legitimate status if you have not measured yet) and `0004` (control protocol) in
   `starter/adr/`. Use numbers from Chapters 3 and 5 where you have them, and say what you
   did not measure.
3. Implement `lint_file` and `lint_dir` in `adr_lint.py`. Report every problem in words a
   colleague understands, not just "invalid".

**Acceptance tests** (`tests/test_adr_lint.py`): the linter accepts a good record and finds
each kind of defect (name, title and number, date, status, missing, empty or misordered
sections, fewer than two options, missing consequences, gaps and duplicates in numbering,
"Superseded by" a record that does not exist); your records in `adr_location.ADR_DIR` pass
the linter and their titles cover the three topics.

**Hints.** Split the text on `## ` headings first, then look inside each section. The hard
part of an ADR is not the format: it is the Options section. If you can list only one
option, you have not made a decision, you have described one.
