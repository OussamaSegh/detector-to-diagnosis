# Release 0.7.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.7.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts (MDQ-PR-041), in order, on the clean commit
`cfb708f` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it:

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-current.json`, `perf-gate.txt`, `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`.
- Part 4: `fuzz/`, eight targets, `fuzz_calibration` new at this release.

`release-checks.txt` is the script's list of checks of the four parts, each ending with its
summary line. Added by hand:

- `part1-1572784/`: the first run of part 1, on `1572784`, which failed. The hardened build's
  tests failed Exercise 10.4's speed test (MDQ-PR-052) and Exercise 32.3's starter passed in a
  starter build made with Unix Makefiles (MDQ-PR-053). Both were fixed in `cfb708f`, on which
  every part then ran. A second start of part 1 on `cfb708f` was cut by a restart of the machine
  and run again from the beginning.
- `ci-run.txt`: the GitHub Actions runs of `cfb708f`.
