# Release 2.3.0 measurements

The evidence of the release record (`docs/regulatory/releases/2.3.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the five parts, in order, on the clean commit
`1926017` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-5.txt` name it.
Every part passed at its first verdict. Parts 2 and 5 started more than once, because the
session's two-hour limit on a background command stopped a run before its verdict (not a failure
under SDP section 8, MDQ-PR-077); part 5's soak kept each block that had its summary and ran the
stopped block again in full (CR-0038). The acceptance criteria failed ACC-04 only; the release
was approved with a deviation (the record, section Deviation).

- Part 1: `run_all.txt`, `product.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-ab/` and `perf-gate.txt` (against book-v2.2.0, interleaved),
  `perf-trend.txt`, `system-tests.txt`, `system-test-report.md` and `.log`, `e2e.txt` with
  `e2e/`.
- Part 4: `fuzz/`, nine targets of 600 s each.
- Part 5: `soak-ab.txt` and `soak-ab/` (the blocks `base-1` to `base-5` of book-v2.2.0's
  programs and `head-1` to `head-5` of the candidate's, each side merged in `base/` and `head/`),
  `soak.txt` (the candidate's soak, ACC-03 and ACC-04) and `soak-compare.txt` (ACC-10).

`release-checks.txt` is the script's list of checks. `acceptance.md` is `tools/acceptance.py`
run on this directory with `--commit 1926017dc0ac`.

The paths of the machine that wrote the evidence are removed by `tools/evidence_paths.py fix`
(CAPA-0008): a home directory reads `~` and the session's scratch directory `$SCRATCH`.

Added by hand:

- `repro/repro.txt`: `tools/repro_check.sh` on 1926017: two builds of the shipped programs in
  two checkouts, identical archives. The archive carries the candidate's version, 2.3.0-dev.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-26.
- `coverage-review.md`: no class B line changed since 2.2.0.
- `ci-run.txt`: the GitHub Actions runs of the candidate.
