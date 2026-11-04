# Release 0.8.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.8.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts, in order, on the clean commit `d262ff0` in one
worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it:

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3, run twice (the second run's files are at the top level): `perf-suite.txt`,
  `perf-current.json`, `perf-gate.txt`, `system-tests.txt`, `system-test-report.md` and `.log`,
  `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

`release-checks.txt` is the script's list of checks, each part ending with its summary line; part
3 appears twice. `acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree
at the candidate commit. Added by hand:

- `part3-first/`: the first run of part 3. Its gate step failed with an empty log (MDQ-PR-058);
  `perf-suite.txt`, `perf-current.json` and `perf-gate.txt` there are the step run again by hand
  right after, with the output kept. The other files are the script's own.
- `perf-interleaved.txt` with `perf-interleaved/`: the performance suites of release 0.7.0
  (`3f7d720`) and of the candidate, built in two worktrees and run one after the other, twice,
  on the same machine the same day, gated against the baseline and against each other.
- `soak-0.7.0.txt` with `soak-0.7.0/`: the 30-minute soak of the programs of release 0.7.0 on the
  same machine, after the second run of part 3, with nothing else running.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the first green commit after it.
