# Exercise 6.3: notes on the reference solution

- **The records.** The reference records are MiniDAQ's own, in `docs/adr/` (0002 queue,
  0003 control protocol, 0007 list-mode file format, plus four more). `adr_location.py`
  points there, so the linter runs on them in every CI run.
- **The linter** works on headings: it splits the text at `## ` and `### ` lines and checks
  presence, order and non-emptiness. Options count either as a numbered list or as `###`
  subsections, since both are common. Directory-level checks (numbering, superseded-by
  targets) need all files and are therefore in `lint_dir`.
- **What a linter cannot check.** That the Context states the forces honestly, that the
  rejected options were real candidates, that the Negative consequences are not a token
  bullet. That is review's job. Reviewers should ask: "what would make us revisit this?" If
  the record does not answer, it is missing its most useful sentence.
- **Proposed records.** 0007 is "Proposed" on purpose: writing down an undecided question,
  with its options, is how you stop a decision from being made by whoever writes the first
  line of code.
