# Release 0.4.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.4.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in two parts, each on a clean commit in its own worktree:

- Part 1 on `61c2e1a` (`commit.txt`): `run_all.txt`, `static-analysis.txt`, `starters.txt`,
  `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt` and `perf-writer.txt`. An earlier part 1 run on
  the same commit stopped when the disk filled up (coverage report and writer benchmark); the
  run kept here is the whole second one.
- Part 2 on `6766495` (`commit-part-2.txt`): `perf-suite.txt`, `perf-current.json`,
  `perf-gate.txt`, `system-tests.txt`, `system-test-report.md` and `.log`, `soak.txt` with
  `soak/`, and `fuzz/`.

`release-checks.txt` is the script's list of checks of both parts. Added by hand:

- `coverage-review.md`: the review of every untaken branch on a changed class B line.
- `perf-ab/`: the interleaved A/B of tag `book-v0.3.0` against `6766495` (`tools/perf_ab.sh`)
  that explains the failed baseline gate.
- `identical-binaries.txt`: the SHA-256 of the programs, benchmarks and fuzz targets of both
  commits, which shows that part 2's results apply to `61c2e1a`.
- `ci-run.txt`: the GitHub Actions run of `61c2e1a`.
- `first-run-643cec8/`: the first release run of 0.4.0, which failed in the stress run and
  found MDQ-PR-032 and MDQ-PR-033.
