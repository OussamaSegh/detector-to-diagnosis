# Release 0.5.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.5.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts (MDQ-PR-041), in order, on the clean commit
`6ef606e` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it:

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-current.json`, `perf-gate.txt`, `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`.
- Part 4: `fuzz/`.

`release-checks.txt` is the script's list of checks of the four parts, each ending with its
summary line. Added by hand:

- `coverage-review.md`: the review of every untaken branch on a changed class B line.
- `perf-ab/`: the interleaved A/B of tag `book-v0.4.0` against `6ef606e` (`tools/perf_ab.sh`, 5
  rounds) that explains the failed baseline gate.
- `ci-run.txt`: the GitHub Actions run of `6ef606e`.

Earlier runs of the release checks for 0.5.0 (on `2c65872`, `a6bdeb5`, `0c5c2e8` and `d5f3e09`)
failed or were cut short and are not evidence; what they found is in MDQ-PR-039 to MDQ-PR-041,
and the review's tests between them found MDQ-PR-042 to MDQ-PR-044.
