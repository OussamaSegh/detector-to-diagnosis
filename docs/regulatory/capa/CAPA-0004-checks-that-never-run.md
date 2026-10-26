# CAPA-0004: Checks that never run, and evidence that outlives its measurement

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-10-25, by the software lead (release checks for 0.3.0) |
| Source | MDQ-PR-014; at the effectiveness check, MDQ-PR-023, MDQ-PR-029 and MDQ-PR-030 |
| Owner | software lead |
| Effectiveness check | release 0.4.0: not effective; again at release 0.5.0 |

## Problem

The release checks for 0.3.0 ran the performance regression gate by hand on the release
candidate `4c3ac87`, and it failed: `BM_Pipeline` ran at 0.44 of its baseline (MDQ-PR-014). The
performance budget and the verification of SRS-PERF-020 in the SRS still quoted 86 M words/s,
measured at tag `ch05`. Interleaved runs on the reference machine
(`measurements/release-0.3.0/pipeline-attribution.txt`) put the whole drop on commit `1b6bcd3`
of Chapter 10, which made the pair stage the coincidence sorter: 96 M words/s just before it,
39 M words/s at it and at the release candidate. The slowdown was intended and the requirement is
still met at 3.8 times; that seven chapters of documents kept the old number, and that no check
said so, was not intended.

## Investigation

**The gate.** `.github/workflows/perf.yml` runs `tools/perf_suite.sh` and `tools/perf_gate.py`
on a self-hosted runner labelled `perf`, and only for a pull request. The repository has no such
runner and its changes are pushed to `main` without pull requests, so the workflow never started
a job, from Chapter 5 to the release. A workflow that never starts shows neither red nor green on
a commit, so nothing reported it. The gate itself works: run by hand it found the regression at
once, and the other four gated benchmarks passed.

**The other checks of SDP section 6.** Each check was traced to where it runs and to what its
output shows:

- Build, tests, static analysis, document control, change requests and CAPA: GitHub Actions jobs
  on every push (`.github/workflows/ci.yml`), each red when it fails; their runs are listed on
  every commit of Part III.
- Fuzzing for a release, the stress run and the performance requirements: run by hand from a
  script in the developer's scratch directory, outside the repository, so a reviewer could not
  see what was run or repeat it.
- Exercise starters: the check printed only ctest's summary (`216 tests failed out of 268`),
  which cannot show the criterion "every starter fails at least one test". Run per starter, the
  default build of the starters had two that passed every test, `ch05/e2_hotspot` and
  `ch10/e4_fast_sorter`: their only failing test measures speed and skips itself in a build
  without optimization. In a `Release` build all 90 starters fail
  (`measurements/release-0.3.0/starters-release.txt`). The criterion was met for the release, but
  the evidence did not show it.

**The evidence.** The verification column of the SRS cites documents; it does not say when the
number was measured or on which commit, so a document can stay correct in form after the software
changed under it. The performance budget gives the tag of each measurement, which is how the stale
row was dated.

## Root cause

A check was counted as in place when it was configured, not when its output was seen: the SDP
listed the regression gate as a verification without saying where it runs or what evidence it
leaves, and nothing distinguished a gate that passed from a gate that never ran. The release
checks that run by hand had no script under change control, and their outputs were summaries
that did not show the pass criterion.

## Correction

The whole pipeline re-measured for release 0.3.0 (performance budget version 2, SRS version 6);
the `BM_Pipeline` entries of `benchmarks/baseline/book-vm.json` replaced with the release
candidate's, with the reason in the budget; the starters checked one by one in a `Release` build.

## Corrective action

`tools/release_checks.sh` runs every release check of SDP section 6 in order on one clean commit,
including the regression gate and the starters one by one in a `Release` build, writes one file
per check, and exits with a failure when a check fails or cannot run. SDP version 4
(`docs/regulatory/sdp.md`, section 6): the release checks are that script, the performance row
includes the gate, and a check wired only into a workflow is not evidence until the run that
produced it is cited in the release record.

## Preventive action

The gate remains in `.github/workflows/perf.yml` for a team that has the runner; its header now
says that without one it never runs and that the release checks run it. The other workflows
were checked: every job of `ci.yml` runs on GitHub's hosted runners on every push, and the
release record cites the run. Benchmarks are not added to `ci.yml`, because a shared runner's
timing is not comparable with a baseline (Chapter 5).

## Verification of the actions

The gate as `tools/release_checks.sh` runs it failed on the release candidate against the old
baseline (`measurements/release-0.3.0/perf-gate-old-baseline.txt`, the `BM_Pipeline` row) and
passed on the released commit against the new one; the script produced the rest of the evidence
of release 0.3.0 in `measurements/release-0.3.0/`. Its starter check reports the two starters
above in a build without a build type. SRS-PERF-020 is unchanged and met; no risk control depends
on the throughput margin (RC-01 counts every loss).

## Effectiveness check

Criterion: the release record of 0.4.0 cites the output of `tools/release_checks.sh` for every
check of SDP section 6 on the released commit, the gate passes or the baseline change has a
reason, and no number in the performance budget or the SRS's verification column is older than
the last change to the code it measures without saying so. Due: release 0.4.0.

Result (2026-10-26, release checks of 0.4.0): **not effective.** The first run of
`tools/release_checks.sh` for 0.4.0 stopped after the writer benchmark and exited with status 0:
the gate, the system test report, the soak and the fuzzing did not run, and nothing said so
(MDQ-PR-029). The same defect had stopped the 0.3.0 run, where it was taken for a restart of
the session. In CI, the document-control job skipped its version check on every run because no
release tag was on GitHub, and passed (MDQ-PR-030); and the performance gate had passed over
benchmarks that did not run (MDQ-PR-023, corrected in Chapter 20). Three more checks that could
not run and reported success: the action made the release checks one script but did not make
that script, or the jobs, fail when they cannot run.

Further action: the release checks fail with status 3 when they stop before the last check, and
the test `tools.release_checks` checks the script (MDQ-PR-029); the document-control job falls
back to the commit of the newest release record and fails if it has neither (MDQ-PR-030); item
5.3 of the code review checklist (version 2) asks of every check that it fails when it cannot
run. The tests that CI skips were reviewed: `tools.postmortem` (no gdb on the runners) and the
speed tests of Exercises 5.2 and 10.4 (unoptimized builds) are skipped by design and run in
`ci/run_all.sh` and the starters' Release build on the reference machine; `tools.sbom` runs in
the `sbom` job, which installs its schema validator.

New criterion: the release record of 0.5.0 cites a complete run of `tools/release_checks.sh` on
the released commit, ending with its summary line, and no problem report between this result
and the release of 0.5.0 has the cause "a check that could not run passed". Due: release 0.5.0.

## Closure

Not closed: the action was not effective at release 0.4.0; the next check is at release 0.5.0.
