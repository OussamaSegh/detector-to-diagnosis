# CR-0025: The performance gate's baseline and the latency limit

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-07, by the software lead |
| Source | release records of 0.8.0 and 0.9.0 (deviations for ACC-04 and ACC-08) |
| Decision | approved, 2026-11-08, software lead |
| Commits | none yet |

## Description

Decide, before release 1.0.0, how the release checks judge performance on a reference machine
whose speed varies from day to day: a new baseline for the regression gate
(`benchmarks/baseline/book-vm.json`), or a gate that compares the candidate with the previous
release run interleaved on the same machine the same day; and whether the latency limit of
SRS-PERF-022 (10 ms at the 99th percentile of every 10 s interval) keeps its value, its margin or
its definition (every interval, or a share of intervals).

The change, as decided:

1. **The gate** of `tools/release_checks.sh` part 3 builds the previous release (the newest
   `book-v*` tag before the candidate, or `PERF_BASE`) next to the candidate and compares the two
   with `tools/perf_ab.sh`: five rounds, interleaved, ten repetitions per side, judged by
   `tools/perf_gate.py` with its threshold (5%) and significance level (0.01) unchanged. A
   regression fails the release checks as before.
2. **The recorded baseline** stays, as the trend: the candidate's samples against
   `book-vm.json` go to `perf-trend.txt`, which the release record explains and the script does
   not judge. Slow drift over many releases, which a release-to-release gate cannot see, is
   bounded by SRS-PERF-020 and SRS-PERF-021, measured against fixed limits with a margin.
3. **SRS-PERF-022** keeps its limit (10 ms) and its interval (10 s) and holds in at least 99% of
   the intervals of an acquisition, not in every one: in the 30-minute soak, one interval of 180
   may be above. ACC-04 (acceptance specification, version 2) judges the share.
4. **The soak** (`tools/soak.py`) counts the intervals above the limit in its summary and records
   with each sample the steal time of the interval (the CPU time the hypervisor gave to other
   guests, from `/proc/stat`), so that a latency peak can be compared with the machine's state.

## Reason

Two releases in a row failed ACC-04 and ACC-08 with no change to the code the benchmarks and the
soak run: at 0.8.0 the programs of 0.7.0 failed the same way on the same day, and at 0.9.0 the
programs of 0.8.0 failed the same benchmark of the gate. Each release was made with a deviation
the software lead approved. A criterion that fails for the machine and not for the code stops
telling the team anything, and a third deviation would make it a formality. The record of 0.8.0
asked for this request if the machine stayed slower.

## Impact analysis

### Requirements

SRS-PERF-022 changes its definition (at least 99% of the intervals; SRS version 27); its limit
and interval do not. SRS-PERF-020 and SRS-PERF-021 do not change. Their verification is repeated
at release 1.0.0, which implements the change.

### Software items and safety class

None: no item of the product changes. The tools of the release checks change:
`tools/release_checks.sh`, `tools/acceptance.py` and `tools/soak.py`; `tools/perf_gate.py` and
`tools/perf_ab.sh` (Chapters 5 and 20) are used as they are.

### Risk

The latency is not a risk control of a hazard in the risk file; the delay before a fault is
noticed is MDQ-PR-006, and it does not depend on this limit. No estimate changes.

### SOUP

None.

### Interfaces and data formats

None.

### Documents

The SRS, version 27 (SRS-PERF-022); the acceptance specification, version 2 (ACC-04); the
development plan, version 14 (section 6, the gate); Chapter 33's table of criteria; the
CHANGELOG. The baseline file does not change: it is kept as the trend.

### Regulatory

None: the intended use and the safety-relevant functions do not change.

## Verification

The criteria applied to the evidence that releases 0.7.0 to 0.9.0 recorded
(`measurements/cr-0025/compare.py` and `compare.txt`, nothing measured again):

| Evidence | Gate against the baseline | Gate against the previous release | Every interval | 99% of the intervals |
|---|---|---|---|---|
| 0.7.0 | pass | (no interleaved run) | pass, 180 of 180 | pass |
| 0.8.0 | fail, energy filter | pass | fail, 165 of 180, up to 55.6 ms | fail |
| 0.7.0's programs on 0.8.0's day | fail, energy filter | | fail, 167 of 180, up to 206.6 ms | fail |
| 0.9.0 | fail, energy filter | pass | fail, 179 of 180, up to 18.0 ms | pass |

The new latency criterion still fails a day like 0.8.0's: it removes one disturbance in a
30-minute soak, not a slow machine. The gate keeps its power on the same data: release 0.9.0's
samples made 7% slower are flagged on 2 of the 6 benchmarks, 10% slower on 5, 15% slower on all
6; 3% slower on none (`compare.txt`).

Tests: `tools.acceptance` (Verdicts.test_the_latency_holds_in_99_percent_of_the_intervals,
Verdicts.test_a_soak_summary_without_the_count_per_interval_is_missing), `tools.release_checks`,
`docs.baseline`, `docs.trace`, `docs.changes`; the whole ctest. Release 1.0.0's checks run the
new gate and soak (`measurements/release-1.0.0/`).

## Decision

Approved on 2026-11-08 by the software lead, from the three options put to them (this change; the
gate only, with the latency in every interval; no change and a third deviation), after reading
the comparison above. The criteria apply from release 1.0.0 on and were decided before its
release checks ran.
