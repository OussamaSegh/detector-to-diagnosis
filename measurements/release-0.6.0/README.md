# Release 0.6.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.6.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts (MDQ-PR-041), in order, on the clean commit
`893413d` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it:

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-current.json`, `perf-gate.txt`, `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`.
- Part 4: `fuzz/`.

`release-checks.txt` is the script's list of checks of the four parts, each ending with its
summary line. Added by hand:

- `gate-rerun/`: the baseline gate run again alone, after the first run shared the machine
  with a build.
- `perf-ab/`: the interleaved A/B of tag `book-v0.5.0` against `893413d` (`tools/perf_ab.sh`, 5
  rounds) that explains the failed baseline gate.
- `coverage-review.md`: the review of every untaken branch on a changed class B line;
  `coverage-review-gaps.txt` is its list after the review's tests, from `coverage-a9c5ba7.txt`
  with `coverage-a9c5ba7/`, the coverage run on `a9c5ba7`.
- `binaries-893413d.txt` and `binaries-a9c5ba7.txt`: the SHA-256 of the `release` and
  `hardened` programs of both commits, identical.
- `stress-tsan-extended.txt`: the stress run on `a9c5ba7` with the longer list of tests of
  CAPA-0001's action at this release.
- `mdq-pr-045-probe.txt`: the old and the fixed watchdog test against a pause added by hand.
- `ci-run.txt`: the GitHub Actions runs of `893413d` and `a9c5ba7`.
