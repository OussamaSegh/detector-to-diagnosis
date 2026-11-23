# Release 2.1.0 measurements

The evidence of the release record (`docs/regulatory/releases/2.1.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`dae4498` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Every part passed at its first verdict. Part 3 and part 4 each started twice and have two
`## part` headers in `release-checks.txt`. The first run was stopped by the session's two-hour
limit on a background command during part 3's soak, after the gate and the system test report;
the second was stopped by the same limit during part 4, after the fuzz build. Neither reached a
verdict, so neither is a failure in the sense of SDP section 8 (MDQ-PR-077), and `resume` ran
the part again. The third run passed part 4.

An earlier run on fbe436b was stopped by hand in part 1, before any verdict, when CI on that
commit failed in Exercise 29.4's test (MDQ-PR-086); the checks were started again on its fix,
dae4498, in a new output directory.

- Part 1: `run_all.txt`, `product.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3:
  - `perf-suite.txt`;
  - `perf-ab/`, the rounds of release 2.0.1 and of the candidate, and the gate;
  - `perf-gate.txt`;
  - `perf-trend.txt`, which has not been a check since CR-0025;
  - `system-tests.txt`, `system-test-report.md` and `.log`;
  - `soak.txt` with `soak/`, 100 minutes since CR-0035, with the per-second measure of
    MDQ-PR-064;
  - `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, nine targets of 600 s each; `fuzz/documents.txt` is the evidence of
  CAPA-0005's effectiveness check.

`release-checks.txt` is the script's list of checks. `acceptance.md` is `tools/acceptance.py`
run on this directory, in the worktree at the candidate commit.

Added by hand:

- `repro/repro.txt`: `tools/repro_check.sh` on dae4498. It made two builds of the shipped
  programs in two checkouts and compared them byte for byte. They are identical. The archive
  carries the candidate's version, 2.1.0-dev; the release commit changes only VERSION and the
  records.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-23.
- `coverage-review.md`: the review of the untaken branches on the class B lines changed since
  2.0.1.
- `ci-run.txt`: the GitHub Actions runs of the candidate.

The measured soaks of 100 minutes for MDQ-PR-064, unpinned and pinned, run before the checks,
are in `measurements/mdq-pr-064/`.
