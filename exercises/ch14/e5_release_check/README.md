# Exercise 14.5 (M, extra): Check the release record

**Goal.** Turn the release section of MiniDAQ's development plan into a check that a release
record must pass before anyone tags a release.

**Time.** 1.5 hours.

**Starter.** `starter/release_check.py` checks the sections, the version line and that every
check of the plan has a row. It does not look at the results, at the evidence or at the
open problem reports.

**Acceptance** (`tests/test_release.py`, run by CTest as `ch14/e5_release_check/<variant>/unittest`;
`tests/fixture/` holds a complete record, its evidence files and three problem reports):
- A complete record passes; a missing or empty section, a tag that does not match the
  version, or a commit that is not 40 hexadecimal digits fails.
- Every check of `REQUIRED_CHECKS` has a row whose result is exactly `pass` (not "fail",
  "skipped" or "pass (2 flaky)") and whose evidence is a file that exists.
- Every open problem report is listed under Known anomalies.
- The SOUP review is dated, and the build is given as exact commands in a code block.

Then answer in `NOTES.md`: which of these checks would you still do by hand, and why?

**Hints.** Read section 8 of `docs/regulatory/sdp.md`. A check like this does not replace the
release review; it makes sure that the review starts from a complete record.
