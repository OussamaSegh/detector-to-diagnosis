# CR-0035: The release soak lasts 100 minutes

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-21, by the software lead |
| Source | problem report MDQ-PR-064; roadmap 2.1.0, theme I |
| Decision | approved, 2026-11-22, by the software lead (the author), in writing in the project |
| Commits | f73e5ed (release checks, acceptance criteria, records, Chapter 33) and the commit that records this |

## Description

The soak of the release checks (`tools/release_checks.sh`, part 3) runs for 100 minutes instead
of 30. ACC-03 requires at least 100 minutes, and ACC-04 judges SRS-PERF-022's share of 99% over
its 600 intervals of 10 s, so six may be above 10 ms, where the 30-minute soak's 180 allowed one.
The requirements' text, the limit of 10 ms and the share of 99% do not change.

## Reason

MDQ-PR-064: releases 0.8.0, 0.9.0 and 1.0.0 failed ACC-04 with no change to the code. With the
per-second measure of the review of 2.0.0, two 100-minute soaks on 2026-11-21 caught peaks and
showed that neither the run-queue wait of the server's threads nor the steal time marks them,
and that pinning the threads makes them worse (`measurements/mdq-pr-064/`). At the programs of
2.0.x, 2 of 1,740 intervals have had a peak: 0.11%, at most 0.36% at 95% confidence, against the
1% the requirement allows. At that rate a 30-minute soak fails a compliant release with a
probability of 1.9% to 14%; a 100-minute soak, with six of 600 allowed, fails it at 0.36% with a
probability of 0.7%. The criterion was right and its sample was too small.

## Impact analysis

### Requirements

None changed. SRS-SYS-003's and SRS-PERF-022's verification text names the 100-minute soak (SRS
version 38). Their verification is repeated by the release soak of 2.1.0.

### Software items and safety class

None. The programs do not change. The release checks script (`tools/release_checks.sh`)
changes, and so do the acceptance criteria that the acceptance evaluator (TL-41) applies.

### Risk

None. SRS-PERF-022 is not a risk control (MDQ-PR-064's evaluation), and no single was lost in any
interval with a peak.

### SOUP

None.

### Interfaces and data formats

None.

### Documents

The acceptance specification (`acceptance.json`, ACC-03 and ACC-04); the SRS (version 38); the
SDP (version 22, section 5's soak); the system test plan (version 6); MDQ-PR-064, closed;
Chapter 33's account of ACC-04; the CHANGELOG. The release checks take about 70 minutes longer.

### Regulatory

The intended use does not change.

## Verification

`tools.acceptance`: `Verdicts.test_the_latency_holds_in_99_percent_of_the_intervals` (six of
600 pass, seven fail) and `Verdicts.test_evidence_below_its_target_fails` (a 30-minute soak
fails ACC-03);
`docs.changes`, `docs.anomalies`, `docs.srs`; the release soak of 2.1.0, evaluated by
`tools/acceptance.py`.

## Decision

Approved by the software lead on 2026-11-22, in writing in the project.
