# Release 1.1.0 measurements

The evidence of the release record (`docs/regulatory/releases/1.1.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh` ran in four parts, in order, on the clean commit `9b9e96d` in one
worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it. Each part ran to
the end at its first attempt on that commit.

- Part 1: `run_all.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-ab/` (the rounds, the pooled `base.json` of release 1.0.0 and
  `head.json` of the candidate, and `gate.txt`), `perf-gate.txt`, `perf-trend.txt` (not a check
  since CR-0025), `system-tests.txt`, `system-test-report.md` and `.log`, `soak.txt` with `soak/`,
  `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, eight targets.

`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `first-run-039e718/`: the summary, acceptance report and soak of a first run of all four parts
  on 039e718, before the internal audit of 2026-11-10 and the document approvals; every part
  passed and 9 of 9 criteria passed. It is not the release's evidence (the audit must come
  first, SDP section 8, item 9). Before that run passed, three attempts stopped for the
  environment, not the product: a container restart killed a detached run; a shallow clone
  failed `docs.changes` (commits named by change requests were missing); and a fresh container
  lacked `libclang-rt-18-dev` and `cppcheck` (the ASan presets exercise and static analysis).
- `repro/`: `tools/repro_check.sh` on 9b9e96d, two builds of the shipped programs in two
  checkouts, compared byte for byte.
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-10.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits before it.
