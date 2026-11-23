# CAPA-0006: CI results on main not read between pushes

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-11-23, by the software lead (internal audit before release 2.1.0) |
| Source | MDQ-PR-085; during the check period, MDQ-PR-091 and MDQ-PR-092 (red runs on main, each reported the same day) |
| Owner | software lead |
| Effectiveness check | release 2.2.0 |

## Problem

The CI failed on every commit pushed to `main` from 9a92709 (2026-11-17) to 13bfdb3
(2026-11-22), about 30 commits, and no one noticed until the internal audit before release 2.1.0
read the CI runs. Two jobs failed: `tests.waits` in the seven build-test jobs, on Exercise 29.4's
test, and `vulnerability-scan`, on eight new OpenSSL findings without a decision.

## Investigation

The CI runs of `main` since book-v2.0.1 were read with the GitHub API: the last green run was
before 9a92709. Each commit's message names the tests run before it was pushed; for the
commits since 9a92709 these were subsets (`ctest -R` with the tests of the change, or the
`docs` tests). `tests.waits` is in the unit suite and would have failed locally; the
vulnerability scan runs only in CI, because the scanner's database cannot be reached from the
development container. The SDP asks for a green CI before a tag (section 8) and says nothing
about when a pushed commit's result is read.

## Root cause

No rule said when a pushed commit's CI result is read, and the local check before a push was a
subset of the suite.

## Correction

6162e1e tags the waits of Exercise 29.4's test and records the eight triage decisions; the SOUP
list's review of 2026-11-23 records the findings.

## Corrective action

`docs/regulatory/sdp.md` version 22, section 5, "Before and after a push": the whole unit suite before pushing a
change to a test, a tool or a controlled document; the CI result of the last pushed commit read
before the next push and at the latest on the day; a failed run on `main` gets a problem report
the same day.

## Preventive action

The same cause could hide a failure of any CI-only job (CodeQL, the arm64 build, the fuzz smoke
test). The rule covers every job of `.github/workflows/ci.yml`, not only the two that failed.

## Verification of the actions

The SDP rule is in version 22, a draft to be approved with release 2.1.0. The CI run on 6162e1e
is read before the release checks start. No requirement or risk control changes.

## Effectiveness check

Criterion: between release 2.1.0 and release 2.2.0, no run of `ci` on `main` stays red past the
day it ran without a problem report, and every commit's message names the whole unit suite or
says why it was not needed.
Due: release 2.2.0.
Result: filled in at the check.

## Closure

Open until the effectiveness check.
