# Release 2.0.1 measurements

The evidence of the release record (`docs/regulatory/releases/2.0.1.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`620dc65` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Every part passed at its first verdict. Part 4 (fuzzing) started three times and has three
`## part 4` headers in `release-checks.txt`. The first run was stopped by the session's
two-hour limit on a background command, after parts 1 to 3 in the same run. The second was
stopped by a restart of the machine. Neither reached a verdict, so neither is a failure in the
sense of SDP section 8 (MDQ-PR-077), and `resume` ran the part again. The third passed.

- Part 1: `run_all.txt`, `product.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3:
  - `perf-suite.txt`;
  - `perf-ab/`, the rounds of release 2.0.0 and of the candidate, and the gate;
  - `perf-gate.txt`;
  - `perf-trend.txt`, which has not been a check since CR-0025;
  - `system-tests.txt`, `system-test-report.md` and `.log`;
  - `soak.txt` with `soak/`, which has the per-second measure of MDQ-PR-064;
  - `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, nine targets, with `fuzz_documents` mode 5 (MDQ-PR-078).

`release-checks.txt` is the script's list of checks. `acceptance.md` is `tools/acceptance.py`
run on this directory, in the worktree at the candidate commit.

Added by hand:

- `repro/repro.txt`: `tools/repro_check.sh` on 620dc65. It made two builds of the shipped
  programs in two checkouts and compared them byte for byte. They are identical. The archive
  carries the candidate's version, 2.0.1-dev; the release commit changes only VERSION and the
  records.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-16.
- `coverage-review.md`: the review of the untaken branches on the class B lines changed since
  2.0.0.
- `ci-run.txt`: the GitHub Actions runs of the candidate.

The measured soak of 100 minutes for MDQ-PR-064, run before the checks, is in
`measurements/mdq-pr-064/`.
