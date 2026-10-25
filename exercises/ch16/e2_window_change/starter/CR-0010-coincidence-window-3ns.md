# CR-0010: Default coincidence window of 3 ns

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-10-25, by the physics lead |
| Source | improvement: fewer randoms at high activity |
| Decision | pending |
| Commits | none yet |

## Description

Change the default coincidence window from 4 ns to 3 ns.

## Reason

Fewer randoms.

## Impact analysis

### Requirements

SRS-SRT-001 does not change: it says "the coincidence window", whatever its value.

### Risk

None: only a default changes.

## Verification

CoincidenceSorter.TheWindowIs3ns.

## Decision

Pending.
