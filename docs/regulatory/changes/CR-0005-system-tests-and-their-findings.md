# CR-0005: System tests of the shipped programs, and the corrections they found

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-25, by the software lead |
| Source | problem reports MDQ-PR-015, MDQ-PR-017, MDQ-PR-018 and MDQ-PR-019; requirement changes (SRS version 8) |
| Decision | approved, 2026-10-25, software lead |
| Commits | f9cd6c7, 68a63e2 |

## Description

MiniDAQ gets system tests that run `minidaq_server`, `minidaq_ctl`, `minidaq_send` and
`minidaq_listmode` in their own processes (Chapter 19), a system test plan, a generated test
report and a soak test. The system tests found three defects, which this request corrects:

- the coincidence sorter takes singles with equal times in crystal order, whatever the order in
  which they arrive (MDQ-PR-017);
- the sequence tracker counts a packet as reordered only when it is used, not when it is a copy
  of a held packet (MDQ-PR-019);
- the link simulator of `minidaq_send` reports the packets it both delayed and duplicated, and
  the readout system test accounts for them (MDQ-PR-018, a test tool).

## Reason

The class B items `ctl` and `server` had no automated test (MDQ-PR-015), and SRS-SYS-004
(reproducible output) could not be met while the sorter's output depended on batch boundaries.
Without the tracker correction, a diagnostic counter misleads the investigation of a link
problem under load.

This request was written after commit f9cd6c7, which already contained the sorter correction and
the new requirements. That is a deviation from the change control procedure (step 2: the impact
analysis comes before the code); it is recorded here rather than hidden, and it is the kind of
slip that internal audit finding A-1 of Chapter 16 describes.

## Impact analysis

### Requirements

Added in SRS version 8: SRS-SRT-013 (ties in crystal order), SRS-CTL-040 to SRS-CTL-044 (the
client's exit status, TLS refusal and `wait`; the server program's options, shutdown and
start-up configuration), SRS-SYS-001 to SRS-SYS-005 (system requirements). Repeated
verification: every SRS-SRT requirement (the sorter's properties and unit tests), SRS-RDO-005
and SRS-RDO-007 (the tracker's tests and the readout system tests).

### Software items and safety class

Changed: `sorter` (CoincidenceSorter::insert), `readout` (SequenceTracker::offer), `sim`
(LinkFaultCounts) and the test tool `minidaq_send`. No class or segregation changes.

### Risk

None. The sorter's two orders of a pair with equal times describe the same coincidence;
`packets_reordered` does not enter the integrity verdict; no risk control changes. The system
tests add evidence for the controls of H-08 (SRS-CTL-041), see the risk file.

### SOUP

None. The system tests use the Python standard library and the platform's `openssl` command to
make test certificates.

### Interfaces and data formats

No change to the control protocol, the configuration schema, the readout format or the list-mode
format. The meaning of the status field `packets_reordered` is corrected to its documented
definition. The report line of `minidaq_send` gains a field at its end.

### Documents

SRS version 8, development plan version 6, system test plan version 1 (new), the design file,
the trace matrix and the known anomalies.

### Regulatory

No change to the intended use or a safety-relevant function.

## Verification

Properties.TheOrderOfTiesDoesNotMatter and Properties.TheSorterFindsWhatTheReferenceFinds (fail
without the sorter correction); SequenceTracker.ALateCopyOfAHeldPacketIsNotReordered (fails
without the tracker correction); SequenceTracker.AccountsForEveryPacketThroughAFaultyLink; the
system tests system.control, system.acquisition and system.readout in all six presets, the
readout tests also 8 times with the CPUs loaded; the coverage report with the system tests
(`measurements/ch19/coverage/`); the soak (`measurements/ch19/soak/`); the tests docs.srs,
docs.trace and docs.anomalies; static analysis.

## Decision

Approved by the software lead on 2026-10-25: the corrections are small and each has a test that
fails without it, and the system tests close the evidence gap of MDQ-PR-015.
