# Release 1.0.0 measurements

The evidence of the release record (`docs/regulatory/releases/1.0.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts, in order, on the clean commit `517cd49` in one
worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it. Each part ran to
the end at its first attempt.

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt` (both builds and the interleaved runs), `perf-ab/` (the rounds, the
  pooled `base.json` of release 0.9.0 and `head.json` of the candidate, and `gate.txt`),
  `perf-gate.txt` (a copy of `perf-ab/gate.txt`), `perf-trend.txt` (the candidate against the
  recorded baseline, not a check since CR-0025), `system-tests.txt`, `system-test-report.md`
  and `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `soak-0.9.0.txt` with `soak-0.9.0/`: the programs of release 0.9.0 (`8d34971`, built in a
  second worktree with the `release` preset), soaked by the candidate's `tools/soak.py` on the
  same machine right after part 3, before part 4, after ACC-04 failed.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits before it.
