# CR-0025: The performance gate's baseline and the latency limit

| Field | Value |
|---|---|
| Status | proposed |
| Requested | 2026-11-07, by the software lead |
| Source | release records of 0.8.0 and 0.9.0 (deviations for ACC-04 and ACC-08) |
| Decision | pending |
| Commits | none yet |

## Description

Decide, before release 1.0.0, how the release checks judge performance on a reference machine
whose speed varies from day to day: a new baseline for the regression gate
(`benchmarks/baseline/book-vm.json`), or a gate that compares the candidate with the previous
release run interleaved on the same machine the same day; and whether the latency limit of
SRS-PERF-022 (10 ms at the 99th percentile of every 10 s interval) keeps its value, its margin or
its definition (every interval, or a share of intervals).

## Reason

Two releases in a row failed ACC-04 and ACC-08 with no change to the code the benchmarks and the
soak run: at 0.8.0 the programs of 0.7.0 failed the same way on the same day, and at 0.9.0 the
programs of 0.8.0 failed the same benchmark of the gate. Each release was made with a deviation
the software lead approved. A criterion that fails for the machine and not for the code stops
telling the team anything, and a third deviation would make it a formality. The record of 0.8.0
asked for this request if the machine stayed slower.

## Impact analysis

### Requirements

SRS-PERF-022 may change (its limit or its definition). SRS-PERF-020 and SRS-PERF-021 do not.
Their verification is repeated at the release that implements the change.

### Software items and safety class

None: no item of the product changes. The tools of the release checks (`tools/perf_gate.py`,
`tools/release_checks.sh`, `tools/acceptance.py`) may change.

### Risk

The latency is not a risk control of a hazard in the risk file; the delay before a fault is
noticed is MDQ-PR-006, and it does not depend on this limit. No estimate changes.

### SOUP

None.

### Interfaces and data formats

None.

### Documents

The SRS (SRS-PERF-022), the acceptance specification (ACC-04, ACC-08), the SDP's release checks,
and the baseline file, each with a new version.

### Regulatory

None: the intended use and the safety-relevant functions do not change.

## Verification

To be stated with the decision: the gate and the soak of releases 0.7.0, 0.8.0 and 0.9.0 side by
side (`measurements/release-0.*/perf-interleaved.txt`, `soak.txt`), and the new criterion applied
to all three.

## Decision

Pending.
