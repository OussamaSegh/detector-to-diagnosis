# CR-0031: Time base monitor and the boards' clock status

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-16, by the software lead |
| Source | hazard H-02, whose residual named a time error that keeps the order of the singles; roadmap 2.0.0, theme C (Chapter 38) |
| Decision | approved, 2026-11-16, under the software lead's standing delegation of 2026-11-15 |
| Commits | in progress; listed when the change is implemented |

## Description

MiniDAQ watches the agreement of the detector blocks' clocks during a run, from the coincidences
and from the boards' phase-locked loops, and reports a run whose times cannot be trusted
(ADR 0037).

1. **Time base monitor** (`minidaq/processing/timing_monitor.hpp`, item processing). Per interval
   of acquisition time and pair of blocks, the shift of the mean time difference of the true
   coincidences (prompts less delayeds, within a half window) from the pair's reference of the
   first intervals; one clock offset per block by weighted least squares with a mean of zero per
   group of connected blocks; chi2 per degree of freedom; a level per block against a warning and
   an alarm limit and the estimate's own uncertainty (SRS-TIM-001, SRS-TIM-002, SRS-TIM-003).
2. **Pipeline.** The pair stage records every batch of coincidences in the monitor and flushes it
   at the end of the run; the monitor never waits for a reader.
3. **Configuration schema 2.1.** An optional `timing_monitor` object (SRS-CFG-016).
4. **Status and integrity** (control API 3.1, new fields only). `timing`: the monitor's snapshot;
   the integrity verdict counts the intervals at alarm.
5. **Register map 1.3** (firmware 1.4). Each board's clock status: the phase-locked loop's lock
   and a count of lock losses. Slow control reads it every cycle; each board in `hardware` reports
   it; a lock loss during a run is an audit event and counts in the integrity verdict.
6. **Simulation.** The detector simulator gives each block a clock error (offset, drift, a step at
   a given time), and `minidaq_send` sets it, so that the system tests and the measurements inject
   known faults.

## Reason

H-02's controls (RC-06, RC-07) find times that wrapped wrongly or singles out of order. A block
whose time base moves during a run keeps the order: a phase-locked loop that loses lock and locks
again a few hundred picoseconds away, a board that restarts its counter, a reference that drifts.
Its coincidences have wrong time differences, true coincidences near the window's edge are lost,
the delayed window no longer estimates the prompt window's randoms exactly, and a time of flight
puts each event at the wrong place along its line. Without the change the run is stored and
reconstructed as if nothing happened.

## Impact analysis

### Requirements

Added: SRS-TIM-001, SRS-TIM-002, SRS-TIM-003, SRS-TIM-004 (status and integrity), SRS-TIM-005
(simulator), SRS-CFG-016 (SRS version 34); the requirements of the clock status are added with
their code. Verification
repeated: the whole unit suite (the pair stage changes) and the system tests of the acquisition.

### Software items and safety class

Items processing (the monitor), pipeline, config, service (status, integrity), hw (register map
1.3, slow control), sim and the app `minidaq_send`. No class changes: processing and pipeline are
class B. The monitor reads the coincidences and changes none of them; the pipeline's tests compare
the coincidences with and without it.

### Risk

Hazard H-02: RC-53 (the time base monitor) and a second control for the clock status, added with
its code, are new protective measures for the sequence "the time base of one block moves during a run", added to H-02's
sequence. The probability after the controls stays P2; the residual names what the monitor cannot
see (a constant offset from the start, which the timing calibration controls; a shift common to
all blocks, which changes no coincidence; a shift below the warning limit; the interval in which
a shift is found). A new failure mode is a false alarm, which stores a good run as incomplete: the
levels need both the limit and 5 standard deviations, and `measurements/ch38/` measures the false
alarm rate of a healthy run.

### SOUP

None.

### Interfaces and data formats

Configuration schema 2.1 (an optional object; a 2.0 file is read as before). Control API 3.1 (new
fields only, ADR 0003). Register map 1.3 (additions only, firmware minor version 1.4, ICD-FEB). The
list-mode format does not change; the run record keeps the status as it is, so it gains the new
fields.

### Documents

The SRS, version 34 and later; ADR 0037; the risk file (H-02); the configuration schema document;
ICD-FEB and the register map; the architecture description and appendix; the trace matrix;
Chapter 38; the CHANGELOG.

### Regulatory

The intended use does not change. The change adds a safety-relevant function (a protective measure
of H-02) and is recorded for the next release (2.0.0).

## Verification

Tests: `BlockOffsets.ExactShiftsGiveTheOffsetsWithAMeanOfZero`,
`BlockOffsets.ASingleChainHasTheUncertaintyOfItsPairs`,
`BlockOffsets.GroupsAreSolvedApartAndALoneBlockIsUnobserved`,
`BlockOffsets.ShiftsThatNoBlockClockExplainsGiveALargeChi2`,
`TimingMonitor.RefusesAConfigurationThatCannotWork`, `TimingMonitor.AHealthyRunStaysNormalInEveryBlock`,
`TimingMonitor.AStepInOneBlockClockIsFoundInThatBlockAndNoOther`,
`TimingMonitor.TheRandomsDoNotDiluteTheShift`, `TimingMonitor.ADriftIsFoundOnceItPassesTheLimits`,
`TimingMonitor.TooFewTruesLeaveTheBlocksUnobserved`,
`TimingMonitor.ASnapshotCanBeTakenWhileTheMonitorRecords`, `Config.TheTimingMonitorIsReadFromSchema21`,
`AcquisitionService.ReportsTheTimeBaseOfEachBlock`,
`RunIntegrity.IntervalsWithABlockClockAtAlarmMakeTheRunIncomplete`,
`BlockClocks.EachBlockStampsWithItsClockAndNothingElseChanges`, `BlockClocks.AClockThatCannotBeIsRefused`,
`ControlProtocol.StatusFieldsMatchTheApiVersion`; the system tests
`test_a_block_whose_clock_steps_is_named_and_the_run_is_incomplete` and
`test_a_healthy_time_base_raises_no_alarm` (system.readout);
`docs.trace`, `docs.baseline`, `docs.changes`, `docs.risk`; the whole ctest; the tests of the
status, the clock status and the simulator are added with their code.

## Decision

Approved on 2026-11-16 by the coordinator under the standing delegation that the software lead
gave on 2026-11-15 for the work towards 2.0.0, after reading the impact analysis above.
