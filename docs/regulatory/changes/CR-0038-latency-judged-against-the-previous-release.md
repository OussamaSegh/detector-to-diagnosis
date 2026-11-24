# CR-0038: The latency is judged against the previous release on the same machine

| Field | Value |
|---|---|
| Status | proposed |
| Requested | 2026-11-24, by the software lead |
| Source | problem report MDQ-PR-096 |
| Decision | pending (roadmap 2.3.0) |
| Commits | none yet |

## Description

The release checks judge ACC-04, the share of the soak's intervals of 10 s whose 99th percentile
of the end-to-end latency is at most 10 ms, on one soak of the candidate alone. This change adds
a soak of the previous release's programs, interleaved with the candidate's on the same machine
in the same session (as the regression gate already does for the benchmarks, CR-0025), and
judges the candidate's count of slow intervals against both the absolute limit of SRS-PERF-022
and the previous release's count, with a test of the difference. The two verdicts stay
apart: a candidate no worse than the previous release that still fails the absolute limit
fails ACC-04, and is released only with a deviation (SDP version 24, section 8); the
comparison says where the failure is, not that the requirement is met.

## Reason

MDQ-PR-096: on 2026-11-24 the candidate of 2.2.0 had 8 and then 11 of 600 slow intervals, where
six are allowed, and a control soak of book-v2.1.0's programs on the same machine had 6, against
3 at their own release and 2 of 1,740 at 2.0.x. The same programs had twice as many slow
intervals on one evening as at their release; a single soak cannot tell the machine's state
from a change of the code, so the criterion stops a release on the machine's state, or passes
one on a quiet day. (The review of 2.2.0, MDQ-PR-099, corrected an earlier reason here: a CPU
wait of 20 ms or more is in 99% of all intervals, slow or not, so it does not show the
machine's state; the control soak does.)

## Impact analysis

### Requirements

None changed: SRS-PERF-022 keeps its limit and share. Its verification gains the comparison.

### Software items and safety class

None: `tools/release_checks.sh`, `tools/acceptance.py` and `docs/regulatory/acceptance.json`
change; no shipped item.

### Risk

None: the latency is not a risk control (MDQ-PR-064's evaluation).

### SOUP

None.

### Interfaces and data formats

None.

### Documents

SDP (section 6, the soak), system test plan, acceptance specification, the release record's
skeleton; their next versions.

### Regulatory

No change to the intended use or to a safety-relevant function.

## Verification

To be planned in the roadmap of 2.3.0: the comparison's test against recorded soaks
(`measurements/mdq-pr-064/`, `measurements/mdq-pr-096/`), and the release checks of 2.3.0.

## Decision

Pending, for the roadmap of 2.3.0.
