# Release 2.2.0 measurements

The evidence of the release record (`docs/regulatory/releases/2.2.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`5647d2e` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Parts 1, 2 and 4 passed at their first verdict; parts 3 and 4 each started twice, because the
session's two-hour limit on a background command stopped a run before its verdict (not a failure
under SDP section 8, MDQ-PR-077).

Part 3 passed every check at its first verdict, but the acceptance criteria failed ACC-04 (8 of
600 soak intervals above 10 ms, six allowed). Under SDP section 8 its investigation is
`rerun-part-3.md` (MDQ-PR-096), and part 3 ran again once, in full: its second verdict failed the
regression gate on `BM_SortFunctor` and ACC-04 again (11 of 600). `first-part-3/` keeps the
first run's soak, performance suite, end-to-end summary and commit; the files at this folder's
top are the second run's. The control soak of book-v2.1.0's programs and the comparison of the
benchmark's machine code are in `measurements/mdq-pr-096/`. The release was approved with a
deviation for both (the record, section Deviation).

- Part 1: `run_all.txt`, `product.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3 (second run): `perf-suite.txt`, `perf-ab/` and `perf-gate.txt` (against
  book-v2.1.0, interleaved), `perf-trend.txt`, `system-tests.txt`, `system-test-report.md` and
  `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, nine targets of 600 s each.

`release-checks.txt` is the script's list of checks. `acceptance.md` is `tools/acceptance.py`
run on this directory, in the worktree at the candidate commit.

Added by hand:

- `repro/repro.txt`: `tools/repro_check.sh` on 5647d2e: two builds of the shipped programs in
  two checkouts, identical archives. The archive carries the candidate's version, 2.2.0-dev.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-24.
- `coverage-review.md`: the review of the untaken branches on the class B lines changed since
  2.1.0.
- `ci-run.txt`: the GitHub Actions runs of the candidate.
