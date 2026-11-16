# Release 2.0.0 measurements

The evidence of the release record (`docs/regulatory/releases/2.0.0.md`). Each text file starts
with the time, the commit and the command, except the JSON files, whose `context` has the time.

`tools/release_checks.sh OUT 600 resume` ran the four parts, in order, on the clean commit
`c977dd9` in one worktree; `commit.txt` and `commit-part-2.txt` to `commit-part-4.txt` name it.
Parts 1, 2 and 4 passed at their first attempt on that commit. Part 3 failed once, on the
performance regression gate alone (`BM_HistogramRecord` at 0.917 of release 1.3.0, p = 0.0057;
its system tests, soak and end-to-end run passed); `perf-ab-first/` keeps that run's rounds and
verdict, and `perf-ab-first/bm_histogram-record.s` the benchmark's machine code, which is the
same in the builds of 1.3.0 and of c977dd9 but for addresses. Run again by hand, alternately, the
two builds measured 2.10 to 2.72 ns (1.3.0) against 2.09 to 2.39 ns (c977dd9). `resume` then ran
part 3 again in full and it passed; its result is the one recorded. During that second run of
part 3 a debug build of the unit tests (`nice`, two jobs) and `llvm-cov` ran on the same machine
for the coverage review: the gate compares two builds interleaved, which share any load, and the
soak's latency passed with that load.

An earlier run on d38fd04 is not evidence of this release: part 1 passed and part 2 failed its
coverage report, because `tools.recon_cpp` ran past its timeout in the coverage build; fixed in
c977dd9, the candidate.

- Part 1: `run_all.txt`, `product.txt`, `static-analysis.txt`, `starters.txt`.
- Part 2: `stress-tsan.txt`, `properties-wide.txt`, `coverage.txt` with `coverage/`,
  `coverage-exercise.txt`, `perf-pipeline.txt`, `perf-writer.txt`.
- Part 3: `perf-suite.txt`, `perf-ab/` (the rounds of release 1.3.0 and of the candidate, and
  the gate), `perf-gate.txt`, `perf-trend.txt` (not a check since CR-0025), `system-tests.txt`,
  `system-test-report.md` and `.log`, `soak.txt` with `soak/`, `e2e.txt` with `e2e/`.
- Part 4: `fuzz/`, nine targets, `fuzz_documents` (CAPA-0005) among them.

`release-checks.txt` is the script's list of checks, each part ending with its summary line.
`acceptance.md` is `tools/acceptance.py` on this directory, run in the worktree at the candidate
commit. Added by hand:

- `repro/`: `tools/repro_check.sh` on c977dd9, two builds of the shipped programs in two
  checkouts, compared byte for byte (the archive itself is not kept here; its SHA-256 is).
- `lock-audit.json`: `tools/lock_audit.py analysis/requirements.lock --json`, 2026-11-16.
- `ci-run.txt`: the GitHub Actions runs of the candidate and of the commits around it.
- `coverage-review.md` with `coverage-review-lines.txt`: the review of the untaken branches on
  the class B lines changed since 1.3.0, from the coverage build of part 2.
- `perf-ab-first/`: the first run of the gate, described above.
