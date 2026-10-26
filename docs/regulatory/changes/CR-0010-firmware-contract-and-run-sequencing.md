# CR-0010: Firmware contract, firmware check and the run's sequencing with the boards

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-26, by the software lead with the firmware lead |
| Source | design review of Chapter 22's hardware port: the software never set the boards' triggers, read every board as the firmware it was written for, and stopped a run without waiting for the boards (fault tree of H-01, events E5 and E6; residual of CR-0009) |
| Decision | approved, 2026-10-26, software lead, firmware lead and risk manager |
| Commits | 904a6c3 |

## Description

An interface control document with the board's firmware, `docs/hw/icd-feb.md` (ICD-FEB, version 1),
records the versions, the control path, the sequences of a run and the data path. The register map
goes to version 1.1: `status.fifo_empty`, `error_flags.fifo_overflow` and the register `fifo_level`
(0x014). The slow control reads `fw_version` and `fifo_level` every cycle, latches a fault on a
board whose firmware is not 1.2 or a later 1.x, switches the boards' triggers when the service asks
(at once, not at the next period), counts and clears FIFO overflows, and writes 0 to `control`
when a fault latches (bias and triggers off). The acquisition service switches the triggers on
after its pipeline has started, checks that the boards did, switches them off at a stop and stops
the pipeline only once every board is drained or a drain timeout has passed, and switches them off
at a fault, at the end of a finite run and at a reset. The integrity verdict counts FIFO overflows
and drain timeouts as losses. The hardware description goes to schema 1.1 (the run's timeouts; for
simulated boards, the firmware version, the FIFO's rates and the fault `stalled_link`); the control
API goes to 2.3 (each board's firmware, triggers and FIFO, and the run's drain timeouts).

## Reason

Software that reads registers of a firmware it was not written for can misread the temperature or
write the bias in the wrong units without an error (H-10). A stop that does not wait for the boards
loses the run's last events where no counter on the host sees them, and the run is judged complete
(H-01).

## Impact analysis

### Requirements

New: SRS-HW-011 (the firmware check), SRS-HW-012 (triggers after the pipeline, confirmed),
SRS-HW-013 (the drain at stop), SRS-HW-014 (triggers off at the run's other ends) and SRS-HW-015
(overflows and drain timeouts are losses), SRS version 13. Changed: SRS-HW-004 (a fault switches
the triggers off too), SRS-HW-007 (the status fields of API 2.3) and SRS-HW-010 (schema 1.1).
Verification repeated: SRS-HW-001 to SRS-HW-010 and SRS-CTL-030.

### Software items and safety class

Changed: hw (class B), service (class B), config (class B). No class or segregation changes. The
slow control's cycle gains two register reads per board and, when the triggers change, one
read-modify-write; the cycle's thread can now be woken before its period ends.

### Risk

H-01 gains RC-30 (the run's edges are inside the run, overflows and drain timeouts are losses).
H-10 gains RC-31 (unsupported firmware latches a fault every cycle). Residual: loss on the network
after the last datagram that reaches the host stays invisible until the board counts what it sent
(ICD section 8, register map 1.2).

### SOUP

None.

### Interfaces and data formats

The register map 1.1 is a compatible addition, but the software now refuses firmware older than
1.2, which implements it; a site with older firmware must update it first (release notes). The
control API 2.3 adds fields only (ADR 0013); clients of 2.2 keep working. The hardware description
1.1 adds keys only; descriptions 1.0 are still read. A stop takes at least one more slow-control
cycle (`measurements/ch24/run_sequence.txt`). The data format does not change.

### Documents

ICD-FEB version 1 (new); ADR 0019 (new) and the ADR index; the register map and its generated table; the
architecture description, version 10; the SRS, version 13; the trace matrix; the risk file (RC-30,
RC-31); the CHANGELOG.

### Regulatory

The intended use does not change. The release notes of 0.5.0 must name the firmware versions the
software supports, and an installation record must include each board's firmware version, which
the status now reports.

## Verification

Unit tests of the slow control (SlowControl.RefusesFirmwareItWasNotWrittenFor,
SlowControl.SwitchesTheTriggersWhenAskedAndSaysWhenItHasDone,
SlowControl.SaysDrainedOnlyOnceTheFifoIsEmpty, SlowControl.CountsFifoOverflowsAsLostDataNotAsAFault,
SlowControl.ALatchedFaultSwitchesTheBiasAndTheTriggersOff), of the service with simulated boards
(HardwareService.TheTriggersAreOnOnlyWhileARunTakesData,
HardwareService.ARunWhoseBoardsDoNotSwitchTheirTriggersOnEndsInAFault,
HardwareService.AStopWaitsForTheBoardsAndADrainThatRunsOutOfTimeIsALoss), of the description
(HardwareConfig.Schema11AddsTheFirmwareTheFifoAndTheRunTimeouts) and of the verdict
(RunIntegrity.TheBoardsLossesCount); the measurement `measurements/ch24/run_sequence.txt`; all
presets of `ci/run_all.sh` and the static analysis.

## Decision

Approved on 2026-10-26 by the software lead, the firmware lead and the risk manager: new risk
controls for existing hazards, in existing class B items, with compatible additions to the
interfaces and one deliberate incompatibility (firmware older than 1.2 is refused), which the
release notes announce.
