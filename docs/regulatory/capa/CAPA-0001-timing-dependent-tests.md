# CAPA-0001: Tests that depend on the speed of the machine

| Field | Value |
|---|---|
| Status | closed |
| Opened | 2026-10-25, by the software lead (internal audit finding A-4) |
| Source | MDQ-PR-010, MDQ-PR-011; at the effectiveness check, MDQ-PR-022, MDQ-PR-028, MDQ-PR-033 and MDQ-PR-034; at 0.5.0, MDQ-PR-039 and MDQ-PR-040; at 0.6.0, MDQ-PR-045; at 0.7.0, MDQ-PR-047, MDQ-PR-048 and MDQ-PR-052 |
| Owner | software lead |
| Effectiveness check | release 0.4.0: not effective; release 0.5.0: not effective; release 0.6.0: not effective; release 0.7.0: not effective; release 0.8.0: effective |

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

Result (2026-11-03, release checks of 0.5.0): **not effective.** Three tests failed for a
timing reason within the criterion's period, all tests of exercises and none of MiniDAQ's own:
Exercise 5.2's speed test in CI (MDQ-PR-034, above), Exercise 12.3's trickle test under
AddressSanitizer with four tests at a time (MDQ-PR-039) and Exercise 10.4's speed test in the
`clang-release` build with four tests at a time (MDQ-PR-040). MiniDAQ's own tests passed the
stress run (66 tests, 100 repetitions under load, `measurements/release-0.5.0/stress-tsan.txt`)
and CI in the period. MDQ-PR-040 shows why the action fell short: the 30% margin rule of 0.4.0
was applied to the test that failed, Exercise 5.2, and the other speed tests that this CAPA
names were not checked against it.

Further action: every timing test that this CAPA names was checked against the margin rule at
this release, on the slowest build and load that runs it:

| Test | Criterion | Measured by a correct solution | Margin |
|---|---|---|---|
| Exercise 5.2, speed | twice the starter's speed | 2.99 times at the slowest (hardened, GitHub runner) | 33% |
| Exercise 10.4, `FastSorter.FastEnough` | 1.9 times the baseline (MDQ-PR-040); since 0.7.0 the 30 M singles/s only where `EX_MIN_SINGLES_PER_S` is set (MDQ-PR-052) | 2.47 to 2.55 times | 30% |
| Exercise 12.3, `FastSink.KeepsUpWithTheSorterAndLosesNothing` | under 500 ms in `write()` | about 110 ms | 4.5 times |
| Exercise 12.3, trickle | max_unsynced + one fsync + 100 ms (MDQ-PR-039) | passes 40 runs alone and the stress run | 100 ms of slack, not 50 |
| Exercise 4.5, clock tests | wide bounds on the conversion, no speed | not a speed test | not applicable |
| Exercise 31.3, `test_is_much_faster_than_the_python_loop` | 15 times a Python loop, best of five, optimized builds only (MDQ-PR-047) | 29 times at the slowest, with four other processes busy | 94% |
| Exercise 3.6, `Worker.IdleWorkerStopsPromptly` (added at 0.7.0) | `stop()` under 100 ms | 8.0 ms at the slowest of 50 runs (1) | 12 times |
| Exercise 6.4, `FrameReader.CostIsLinearInTheBytesReceived` (added at 0.7.0) | 4 times the frames in under 8 times the time plus 50 ms | the limit was at least 2.9 times the time taken, in 20 runs (1) | 194% |
| Exercise 8.3, `Randoms.LinearTime` (added at 0.7.0) | under 1 s | 36 ms at the slowest of 30 runs (1) | 28 times |
| Exercise 12.3, `FastSink.KeepsUpWithTheSorterAndLosesNothing`, slow calls (added at 0.7.0) | at most 2 `write()` calls of 20 ms or more | 0 in 20 runs (1) | 2 calls |
| Exercise 12.4, `test_two_bit_errors_in_a_block` (added at 0.7.0) | under 60 s | 1.55 s at the slowest of 5 runs (1) | 39 times |
| Exercise 19.5, replay at speed 2 and 0 (added at 0.7.0) | under 0.39 s and under 0.15 s, times `MINIDAQ_TEST_TIME_FACTOR` | 0.200 s and 0.2 ms at the slowest of 10 runs (1) | 95%, and 750 times |

(1) Measured on 2026-11-04 in the `Release` build of the exercises on the book machine (4 CPUs)
with six busy processes running, by printing the measured time from a temporary copy of the
test; the debug and sanitizer builds of CI passed the same tests on every run of Part VII.

Item 4.6 of the code review checklist covers a new timing test; the table above is the review
of the existing ones, which the rule had left out.

New criterion: no test fails for a timing reason in CI, in the release checks or in the stress
run between this result and the release of 0.6.0, and every timing test added in Part VI is in
the table above with its margin. Due: release 0.6.0.

Result (2026-11-03, release checks of 0.6.0): **not effective.** One test failed for a timing
reason within the criterion's period, and it is one of MiniDAQ's own:
`ServiceManager.TheWatchdogPingsOnlyWhileEveryLoopBeats`, once in CI, in the `gcc-cxx23` job
on ec4c2e6 (MDQ-PR-045). It is not a speed test. It read the record of the watchdog's callback
as soon as it saw the watchdog's datagram, which the same thread sends just before; a pause of
that thread between the two made it fail. The failure was found only at this check, by reading
every failed CI run of Part VI job by job: the same run failed every job for another reason
(Exercise 6.3's solution), and only that reason was investigated at the time. Part VI added no
timing test (its tests of calibration, corrections and reconstruction compare values, not
times; its waits use `test_support::patience`), so the table above needs no new row. The other
tests that record a callback under a mutex were read for the same pattern: the audit records of
`test_acquisition_service.cpp`, `test_control_protocol.cpp` and `test_security.cpp` are written
on the thread that answers the command, before the answer, so the test that has the answer has
the record.

Further action:

- MDQ-PR-045's test waits for each output it checks (`test_health.cpp`).
- Code review checklist, version 3, item 4.7: a test that waits for one output of another
  thread waits again for each further output it checks.
- The stress run of the release checks (`tools/stress_tests.sh`) also repeats the
  `ServiceManager`, `Health` and `SlowControl` tests, which start threads and were outside it
  since Chapter 25; it would have run this test 100 times under load. Run for 0.6.0 on the fixed
  commit (`measurements/release-0.6.0/stress-tsan-extended.txt`).
- A failed CI run is investigated job by job until every failure has a cause, not only the
  first one found (SDP, version 10, section 7).

New criterion: no test fails for a timing reason in CI, in the release checks or in the stress
run between this result and the release of 0.7.0, and every timing test added in Part VII is in
the table above with its margin. Due: release 0.7.0.

In the period: Exercise 31.3's speed test, added in Part VII, failed in CI's debug build
(MDQ-PR-047). It had been written without the rules of this CAPA: it timed an unoptimized module,
from one run, with no measured margin. It is fixed and is now a row of the table above. The
result at 0.7.0 counts the failure.

Also in the period: Exercise 21.3's concurrent snapshot test failed in a local run of every test
with other tests building in parallel (MDQ-PR-048). It is the defect of MDQ-PR-028, in a copy of
that test in the exercises, which the search for other instances in 0.4.0 did not cover and the
stress run does not select. Rule 5.6 is still enforced by review only. The result at 0.7.0 counts
this failure too.

Further action in the period, ahead of the check at 0.7.0:

- `tests.waits` (`tools/check_test_waits.py`) now enforces rule 5.6 and the margin rule too: a
  clock read in a test states its kind (`// clock: deadline`, `speed`, `measure`, `data` or
  `minimum`) and a thread start states why the test does not depend on when the thread runs
  (`// threads: joined` or `started`). Every test of MiniDAQ, of the reconstruction library, of
  the analysis package and of the exercises was read and tagged: 57 clock reads and 33 thread
  starts. A `speed` tag names a row of the table above.
- Reading every clock read found six speed tests that the table did not list, all in the
  exercises (Exercises 3.6, 6.4, 8.3, 12.3's slow calls, 12.4 and 19.5). Each was run under load
  and is now a row of the table, with its margin; none was below 30%.
- The gate self-test plants an untagged clock read (fault `clocks`) as well as an untagged
  sleep (fault `waits`).

Result (2026-11-04, release checks of 0.7.0): **not effective.** Three tests failed for a timing
reason within the criterion's period, all tests of exercises: Exercise 31.3's speed test in CI
(MDQ-PR-047), Exercise 21.3's concurrent snapshot test in a local run (MDQ-PR-048) and, in part 1
of these release checks, Exercise 10.4's speed test in the hardened build (MDQ-PR-052). The last
had a second criterion, an absolute rate with no margin, that the table did not list: a row now
names every criterion of its test, and the review of every clock read above was repeated for
tests with more than one assertion on a time or a rate (none other found). Neither
is MiniDAQ's own; MiniDAQ's tests passed CI in the period and the stress run of the release
checks (`measurements/release-0.7.0/stress-tsan.txt`). Both failures share the cause that the
results at 0.4.0 to 0.6.0 found: a rule that is checked by review only is not applied to every
test, and a copy of a test outside the place that the search for other instances looked in
keeps the defect, and a review of a test against a rule can stop at the first assertion it
checks. The table above now lists every speed test and every criterion, Part VII's included.

The action of this period is the first that checks the whole cause mechanically: every clock
read and thread start in every test states why it does not depend on the machine's speed, and
`tests.waits` refuses one that does not, in MiniDAQ's tests, in the other packages and in the
exercises alike. Its effect can be judged only over a period that starts after it.

New criterion: no test fails for a timing reason in CI, in the release checks or in the stress
run between this result and the release of 0.8.0; every test added in Part VIII passes
`tests.waits`, and every `speed` tag names a row of the table above. Due: release 0.8.0. If the
criterion holds, the CAPA is closed as effective at 0.8.0; if a test fails for a timing reason
that `tests.waits` accepted, the cause is analyzed again from the start.

Result: **effective** (2026-11-04, release checks of 0.8.0). Every failed run of the period was
read job by job: no test failed for a timing reason in CI, in the release checks or in the stress
run (95 concurrent tests, 100 repetitions each under ThreadSanitizer on a loaded machine,
`measurements/release-0.8.0/stress-tsan.txt`). The failures of the period had other causes: CI's
build jobs lacked SciPy for the daily QC inside `system.e2e` (MDQ-PR-056), a fuzz target's
oracle was wrong (MDQ-PR-057), `docs.version` failed on the commit that recorded the tag of
0.7.0 before VERSION moved on, and the document gate of `gates` failed once on a design file
that did not yet index the requirements baseline. Part VIII added no speed test, and every
test it added passes `tests.waits`. The performance regression gate and the latency limit of
SRS-PERF-022 failed in part 3 of the release checks because the reference machine was slower and
noisier that day (the programs of release 0.7.0 failed both the same way on it); they are
measurements of the machine's speed by design, not tests that this CAPA covers, and the release
record treats them as a deviation.

## Closure

Closed on 2026-11-04 by the software lead at release 0.8.0: the criterion is met over the first
period after the mechanical check. The guards stay in force (`tests.waits` with its tags for
clock reads, thread starts and sleeps, the margin table, the gate self-test's faults `waits` and
`clocks`); a test that fails for a timing reason opens a new problem report and, if its cause is
this one, a new CAPA.
