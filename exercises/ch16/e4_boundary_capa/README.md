# Exercise 16.4 (M): A CAPA for values at the limits of their types

**Goal.** MDQ-PR-001 (`6e688` crashed the configuration reader) and MDQ-PR-002 (a sequence jump of
exactly 2^31) were fixed one at a time. Write the CAPA that asks why both got through, and add
the rules to the CAPA checker that keep a CAPA from being closed on a check that cannot fail.

**Time.** 90 minutes.

**Starter.** `starter/capa.py` has the rules of `tools/check_capa.py` and a TODO for two more.
`starter/CAPA-0003-boundary-inputs.md` is a first draft with most of the classic CAPA mistakes.

**Acceptance** (`tests/test_capa.py`, run by CTest as `ch16/e4_boundary_capa/<variant>/unittest`):
- `check()` also reports an effectiveness check whose due date (the field and the `Due:` line)
  is not a date `YYYY-MM-DD` or `release X.Y.Z`, a criterion with neither a number nor a named
  test or check, and a criterion with a word from `VAGUE`. The repository's CAPA-0001 (copied to
  `tests/`) still passes.
- `CAPA-0003-boundary-inputs.md` passes every rule, names both problem reports, investigates
  every input function (start from `fuzz/README.md`), finds a root cause about limits, changes
  `docs/coding-standard.md` and the seeds in `fuzz/corpus/`, and is not closed.

`tests/problem-reports.json` already marks MDQ-PR-001 and MDQ-PR-002 with `"capa": "CAPA-0003"`,
as you would in the repository; `tests/files.txt` lists the repository's files.

Then answer in `NOTES.md`: your manager asks you to close the CAPA today, since both defects are
fixed. What do you answer?

**Hints.** Read the starter's draft against the CAPA procedure in
`docs/regulatory/capa/README.md`: which sentence is a correction pretending to be a corrective
action, and which is a root cause that stops one question too early?
