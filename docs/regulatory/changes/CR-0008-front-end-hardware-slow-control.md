# CR-0008: The front-end boards' registers, their slow control, and the hardware status (API 2.2)

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-26, by the software lead |
| Source | new function: hazard H-10 (detector gain drifts with temperature), from the system requirements of the scanner, which ask for a gain that stays within its calibration while the room and the electronics warm up (assumption: confirm with team) |
| Decision | approved, 2026-10-26, software lead and risk manager |
| Commits | b27d6ad |

## Description

MiniDAQ talks to the front-end boards for the first time. The registers of a board are
specified once, in `hw/feb.toml`, from which a generator (`tools/regmap_gen.py`) writes typed
C++ definitions and a document. Code reaches the registers through a bus interface, implemented
by a memory-mapped bus for a UIO device or a PCI resource file, and by a simulated board for tests
and demonstrations. A slow-control loop sets each board's SiPM bias from its temperature every
100 ms, so that the overvoltage, and with it the gain, stays constant; it latches a fault and
switches the board's bias off when a board stops answering, has the wrong identity, is too hot or
reports a sensor that cannot be believed, draws too much current, or cannot reach or hold its
setpoint. The acquisition service does not start a run while a board is not ready, stops a run
on a hardware fault (fault source `hw`), and acknowledges the fault on reset. The status and the
run record gain a `hardware` field (control API 2.2). The server reads the description of the
hardware from a new option, `--hardware FILE`.

## Reason

A SiPM's breakdown voltage rises by about 34 mV per degree; at an overvoltage of 2.7 V a fixed
bias loses about 1.3% of gain per degree, and the 511 keV photopeak moves relative to the energy
window. Without compensation, a scanner whose detectors warm by a few degrees during the day
counts a different share of its events in the morning than in the afternoon, without any error
(H-10). The bias supply is also the part of the front end that can damage the detectors if it is
left on in a fault, so the software that controls it must be the part that switches it off.

## Impact analysis

### Requirements

New: SRS-HW-001 to SRS-HW-010 (SRS version 11). Verification repeated: SRS-CTL-033 (the status
fields of the API version, which gain `hardware`), SRS-CTL-011 and SRS-DIAG-004 (faults and their
source in the flight recorder), and SRS-CFG-001 to SRS-CFG-004, whose reader is moved to a header
shared with the hardware description.

### Software items and safety class

New item `hw` (class B): the register layer, the buses, the simulated board, the slow control,
the reader of the hardware description and the adapter that connects them to the service. Changed:
service (start refusal, fault, status), protocol (the version), core (two flight recorder codes),
config (the shared reader), server (the option). No class or segregation changes. The slow control
runs on its own thread and never on the data path; the service polls it from its monitor thread.

### Risk

H-10 is new, with controls RC-26 (compensation), RC-27 (faults switch the bias off) and RC-28 (no
data is taken while a board is not ready or has a fault). H-05 (acquisition interrupted): a
hardware fault now stops a run, which is the intended effect; a warning does not. H-01 (data lost
without notice): a run stopped by a hardware fault is incomplete and says so in its integrity
verdict, as for every other fault.

### SOUP

None. The generator uses Python's standard `tomllib` (Python 3.11 or later), which the tool list
records as TL-25.

### Interfaces and data formats

The control API becomes 2.2: one new status field, always present (null without hardware); no
request or response changes otherwise, so 2.0 and 2.1 clients keep working (ADR 0003, ADR 0013).
The hardware description is a new input with its own schema version, 1.0. The register map of the
front-end board is an interface with the firmware team (`docs/hw/feb-register-map.md`, version
1.0); this book's map is an example, and the real one comes from the board's documentation
(assumption: confirm with team). The list-mode format and the acquisition configuration do not
change.

### Documents

ADR 0017 (new); the ADR index; the SRS, version 11; the trace matrix; the risk file (H-10); the
software items (`hw`) and the layers; the tool list (TL-25); the register map document; the
CHANGELOG.

### Regulatory

The intended use does not change. The software now controls a high-voltage supply of the detector
electronics; whether the bias limits and the switch-off belong in the hardware safety concept of
the scanner (IEC 60601-1) rather than in software alone is a system decision (assumption: confirm
with team). The board's own protection, which switches its bias off above 60 C whatever software
does, is modeled by the simulated board and assumed of the real one.

## Verification

Unit tests of the registers (Registers.FieldsPutTheirBitsWhereTheMapSays,
Registers.AFieldWriteReadsTheRegisterAndWritesItBackOnce and compile-time checks), of the
memory-mapped bus (MmioBus.EachAccessIsOneLoadOrStoreAtTheRegistersOffset,
MmioBus.RefusesAccessesOutsideTheMapOrNotAligned), of the simulated board
(FakeBoard.FailsLikeRealBoardsFail), of the slow control
(SlowControl.KeepsTheOvervoltageConstantAsTheTemperatureMoves,
SlowControl.LatchesAFaultForEachWayABoardFails,
SlowControl.AnAcknowledgedFaultClearsOnlyWhenItsCauseHasGone), of the description
(HardwareConfig.ReportsEveryProblemWithItsLocation) and of the service with simulated boards
(HardwareService.AHardwareFaultStopsTheRunAndAResetAcknowledgesIt,
HardwareService.StatusAndRunRecordShowEachBoard); the generator's tests and the check that the
committed header is current (docs.regmap); the system test of a board that overheats during a
run (`minidaq/tests/system/test_hardware_system.py`); all presets of `ci/run_all.sh` and the
static analysis.

## Decision

Approved on 2026-10-26 by the software lead and the risk manager: a new class B item that
implements risk controls of a new hazard, verified with simulated boards; tests on a real board
are part of the integration with the firmware team.
