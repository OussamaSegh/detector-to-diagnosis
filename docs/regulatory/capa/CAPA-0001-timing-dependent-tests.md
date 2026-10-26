# CAPA-0001: Tests that depend on the speed of the machine

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-10-25, by the software lead (internal audit finding A-4) |
| Source | MDQ-PR-010, MDQ-PR-011; at the effectiveness check, MDQ-PR-022, MDQ-PR-028, MDQ-PR-033 and MDQ-PR-034 |
| Owner | software lead |
| Effectiveness check | release 0.4.0: not effective; again at release 0.5.0 |

## Problem

Two tests failed after they had been merged, each once, with the code under test correct:
`Pipeline.DropPolicyCountsEveryLostWord` on a fast GitHub runner (MDQ-PR-010) and Exercise 10.4's
`FastSorter.FastEnough` on the shared book machine (MDQ-PR-011). Both were fixed at once and
neither was recorded as a problem report, which the internal audit found (A-4).

## Investigation

Every `sleep_for` in `minidaq/tests/` and in the exercises' tests was read (18 places), and the
threaded tests were run under load with `tools/stress_tests.sh`: twice as many busy loops as
CPUs, 16 tests at a time, each test repeated until it fails. At tag `ch15`, the ThreadSanitizer
build failed 2 of 48 tests in 100 repetitions (`measurements/ch16/stress-before-tsan.txt`):

- `AcquisitionService.StatusReportsTheLastIntervalSeparately` slept 150 ms and then asserted that
  a latency interval with data had been reported;
- `PacedSource.NeverDeliversAheadOfTheClock` asserted that the source had delivered 80% of the
  words due in 0.2 s, which depends on how often the test's own thread runs.

Reading found the same pattern, a fixed sleep followed by an assertion that something happened,
in four more tests that the stress run did not catch (`Pipeline.StopRequestDrainsInFlightData`,
`Pipeline.SourceWithNoDataDoesNotHang`, `Pipeline.DestructorStopsARunningPipeline`,
`AcquisitionService.DestructionStopsARunningAcquisition`), and the throughput assertion in
`ReplaySource.RealTimeRateAndPacing`. The exercises' stress run failed
`FastSink.KeepsUpWithTheSorterAndLosesNothing` once in 30 repetitions
(`measurements/ch16/stress-before-ex.txt`); it measures the time that `write()` calls take,
which is what Exercise 12.3 asks for.

## Root cause

The coding standard said nothing about time in tests, and nothing checked it: a test was
accepted when it passed on the author's machine and in CI, so an assumption about relative speed
held until a faster or busier machine broke it. The failures were fixed one by one because no
procedure asked whether the cause could act elsewhere.

## Correction

The seven tests above wait for the condition they need with `test_support::eventually`, with a
deadline of 10 s that only a hang reaches, or assert the requirement (no word before it is due, and
a due word is delivered) instead of a throughput.
`AcquisitionService.StatusReportsTheLastIntervalSeparately` checks the "no interval yet" condition
only when its own thread was not delayed.

## Corrective action

Rule 5.5 of `docs/coding-standard.md`: a test never asserts after a fixed sleep; every sleep in a
test states its reason (`// sleep: poll`, `minimum`, `device` or `hides only`). The test
`tests.waits` (`tools/check_test_waits.py`) fails for a sleep without a reason, in MiniDAQ's tests
and the exercises' tests. The waiting helper is `minidaq/tests/unit/eventually.hpp`.

## Preventive action

`tools/stress_tests.sh` runs the threaded tests under load before each release (SDP section 6,
with the fuzzing and the performance measurements), so that a timing assumption fails on the
book machine before it fails in CI. Tests of a timing property by design (Exercises 4.5, 10.4,
12.3) stay, and are named in the stress run's record.

## Verification of the actions

All six CI presets and static analysis pass with the changed tests. The changed tests still verify
their requirements: SRS-PIPE-012, SRS-CTL-011 and SRS-SIM-002 have the same assertions on the
outcome, and only the waiting changed. The stress run after the correction, at commit `c957527`,
passed all 51 tests (the threaded tests and, new, the protocol tests) in 100 repetitions under the
same load (`measurements/ch16/stress-after-tsan.txt`); the exercises' run passed 30 repetitions
(`measurements/ch16/stress-after-ex.txt`), which does not show that
`FastSink.KeepsUpWithTheSorterAndLosesNothing` cannot fail again: it was not changed.

## Effectiveness check

Criterion: the stress run of the ThreadSanitizer build with 100 repetitions passes at the commit
that implements this CAPA, and no MiniDAQ test fails in CI for a timing reason between that
commit and the release of 0.4.0 (CI history and problem reports).
Due: release 0.4.0.

Result (2026-10-26, release checks of 0.4.0): **not effective.** The stress run passed at the
CAPA's commit (`measurements/ch16/stress-after-tsan.txt`), but two tests failed for a timing
reason after it. Exercise 5.2's speed test had a budget that held only on the reference machine
and failed on a GitHub runner (MDQ-PR-022, corrected in Chapter 20); and the flight recorder's
concurrent snapshot test, written in Chapter 21, took its snapshots before its writer threads
had started in the coverage build (MDQ-PR-028). The stress run of the release checks then failed
`AcquisitionService.DefaultAdaptersRunAtTheConfiguredRate`, whose 5-second wait was too short
under ThreadSanitizer and load (MDQ-PR-033); eighteen waits had deadlines of 5 or 10 s. Rule 5.5 covers waiting and sleeping; neither
failure had a wait to find, so `tests.waits` could not see them. The cause of the CAPA is
broader than its first action: a test that assumes how fast the machine or a thread is.

Further action: every wait in the tests uses `test_support::patience`, now 60 s, so that only a
hang reaches it (MDQ-PR-033); rule 5.6 of the coding standard (version 4) and item 4.6 of the code review
checklist (version 2): a test that starts threads waits until each has started before it checks
what they did; a speed test compares with a budget that the slowest machine that runs it can
meet, or runs only where its budget holds (MDQ-PR-022's resolution). The coverage build stays in
the release checks because it is the slowest build and starts threads late.

New criterion: no test fails for a timing reason in CI, in the release checks or in the stress
run between this result and the release of 0.5.0. Due: release 0.5.0.

Later the same day: the release checks of 0.4.0 on 6766495, after MDQ-PR-033, passed the stress
run (100 repetitions, `measurements/release-0.4.0/stress-tsan.txt`). Then Exercise 5.2's speed test
failed once in CI, in the hardened build on a GitHub runner, at 2.99 times the starter's speed
against 3 (MDQ-PR-034): its criterion was relative since MDQ-PR-022 but had no margin. That is a
failure within the new criterion's period, and the result at 0.5.0 counts it. Further action: a
speed test leaves a margin of at least 30% between its criterion and what a correct solution
reaches on the slowest machine that has run it; Exercise 5.2 asks for twice the starter's speed.

## Closure

Not closed: the action was not effective at release 0.4.0; the next check is at release 0.5.0.
