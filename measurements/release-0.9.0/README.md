# Release 0.9.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.9.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts, in order, on the clean commit `c8d0800` in one
worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it:

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-current.json`, `perf-gate.txt`, `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

Part 1 was started twice before it ran to the end: the machine restarted under the first two
attempts, before any preset had finished building; the third ran on a fresh output directory.
`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `perf-interleaved.txt` with `perf-interleaved/`: the performance suites of release 0.8.0
  (`5770582`) and of the candidate, built in two worktrees and run one after the other, twice,
  on the same machine the same day, after part 4, gated against the baseline and against each
  other.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits before it.
