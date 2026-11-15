# Release 1.3.0 measurements

The evidence of the release record (`docs/regulatory/releases/1.3.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`ced71e9` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Parts 1 to 3 ran to the end at their first attempt on that commit. Part 4 was stopped during its
first run by the session's time limit for a background command, after the fuzz build and before
the first target; `resume` then ran part 4 again in full, and its result is the one recorded.

Two earlier runs on earlier commits are not evidence of this release, and are recorded in the
internal audit of 2026-11-15: on 9034920 the run stopped in part 1 when the machine restarted,
and was abandoned because CI had found MDQ-PR-069; on 895eaee parts 1 and 2 passed and part 3
failed the performance regression gate (MDQ-PR-070, `BM_DecodePacked/65536` at 0.842 of
release 1.2.0). Both are fixed in the candidate.

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-ab/` (the rounds of release 1.2.0 and of the candidate, and
  the gate), `perf-gate.txt`, `perf-trend.txt` (not a check since CR-0025), `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `repro/`: `tools/repro_check.sh` on ced71e9, two builds of the shipped programs in two
  checkouts, compared byte for byte.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-15.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits before it.
- `coverage-review.md` with `coverage-review-lines.txt`: the review of the untaken branches on
  the class B lines changed since 1.2.0, from the coverage build of part 2.
