# Release 1.2.0 measurements

The evidence of the release record (`docs/regulatory/releases/1.2.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`31527cc` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Each part ran to the end at its first attempt on that commit.

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-ab/` (the rounds of release 1.1.0 and of the candidate, and
  the gate), `perf-gate.txt`, `perf-trend.txt` (not a check since CR-0025), `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `repro/`: `tools/repro_check.sh` on 31527cc, two builds of the shipped programs in two
  checkouts, compared byte for byte.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-15.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits before it.
