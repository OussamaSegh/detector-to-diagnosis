# CR-0038: The latency is judged against the previous release on the same machine

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-24, by the software lead |
| Source | problem report MDQ-PR-096 |
| Decision | approved, 2026-11-24, by the coordinator under the software lead's standing delegation (2026-11-23) |
| Commits | e14eb43 (Theme L); verified by the release checks of 2.3.0 |

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

As implemented (roadmap 2.3.0, Theme L): the soak becomes part 5 of the release checks. The
previous release (the newest `book-v*` tag before the candidate) is built from its tag in a
worktree under OUT, and `tools/soak_ab.py` runs the two in 5 blocks of 20 minutes each, in the
order A B, B A, A B, ... (as `tools/perf_ab.sh`); each block is one run of `tools/soak.py`. A
block with its summary is kept, so a run stopped by the two-hour limit continues at the block it
was in. The candidate's blocks, as one soak, are `soak.txt` (ACC-03, ACC-04); its memory trend is
the slope pooled within the blocks after the warm-up of each. `soak-compare.txt` is ACC-10:
Fisher's exact test, one-sided, alpha 0.05, with the power to find a doubled rate stated.

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

None: `tools/release_checks.sh`, `tools/acceptance.py`, `tools/release_record.py`,
`tools/release_facts.json`, the new `tools/soak_ab.py` and
`docs/regulatory/verification/acceptance.json` change; no shipped item.

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

The comparison's tests against the recorded soaks (`measurements/mdq-pr-064/`,
`measurements/mdq-pr-096/`), split into blocks: `tools/test_soak_ab.py`; the acceptance rules,
`tools/test_acceptance.py`; the five parts and their resume, `tools/test_release_checks.py`; the
record's row, `tools/test_release_record.py`; then the release checks of 2.3.0.

The tests that verify it include `Recorded.test_the_rerun_of_2_2_0_fails_acc_04_but_not_acc_10`,
`Recorded.test_the_busy_soak_as_candidate_against_the_quiet_one_fails_acc_10`,
`Fisher.test_the_one_sided_p_is_that_of_the_enumerated_tables`,
`Memory.test_a_leak_in_every_block_fails_the_side`,
`Blocks.test_a_stopped_run_continues_at_the_block_it_was_in`,
`Verdicts.test_the_candidate_is_compared_with_the_previous_release`,
`Verdicts.test_the_soak_is_part_5_and_a_run_without_it_fails` and
`ReleaseChecks.test_each_part_runs_only_its_own_checks`.

## Decision

Approved on 2026-11-24 by the coordinator under the software lead's standing delegation ("I am
the customer, you are the planner and builder, you approve and decide", 2026-11-23), with the
roadmap of 2.3.0, on the impact analysis above. The soak in blocks is a change of how ACC-03 is
measured, not of SRS-SYS-003: the 8-hour run stays with the system test on the acquisition PC.
