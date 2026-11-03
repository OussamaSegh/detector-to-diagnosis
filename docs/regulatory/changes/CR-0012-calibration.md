# CR-0012: Per-crystal energy and timing calibration, applied by the server, with its procedure

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | design review of the data path: energies were the board's code times 0.5 keV and times the board's times, so each crystal's gain, its SiPM's saturation and each channel's delay reached the energy window, the coincidence window and the list-mode data uncorrected (hazard H-11, new) |
| Decision | approved, 2026-11-03, software lead and risk manager |
| Commits | a4e9eac, 689e79d, 8294fd8, c55d36b, 154c15b and the commit that adds this record |

## Description

A calibration table (`processing/calibration`) holds each crystal's energy curve, a quadratic in
the board's energy code, and its channel delay, with the table's identity, scanner serial and
validity; its file format is specified in `docs/formats/calibration.md` and read by
`config/calibration_file`, which checks its CRC-32 and the limits of a working detector. The
acquisition configuration (schema 1.4) names the table and the scanner; the acquisition service
refuses a table for another scanner or out of date. The pipeline's decode stage applies the table
to every single, and the sort stage holds back the spread of the delays so that no single is made
late. A photopeak monitor gives each block's mean calibrated photopeak energy in the status
(control API 2.4) and names the blocks that drift. The run record and the list-mode metadata
name the table. The procedure that makes a table, `tools/calib`, is a new in-house tool (TL-29,
class T3) with acceptance criteria. `minidaq_sim` simulates an uncalibrated detector (gain spread,
saturation, delays) and writes the truth.

## Reason

Uncalibrated, the summed photopeak is 19.4% FWHM wide instead of 10.8%, the energy window keeps a
different share of each crystal's events, and true coincidences fall outside the coincidence
window (measurements/ch26): quantitative values and uniformity are wrong without an error (H-11).

## Impact analysis

### Requirements

New: SRS-CAL-001 to SRS-CAL-007 and SRS-SIM-022 (SRS version 15). No existing requirement changes.
Verification repeated: the pipeline and the sorter (SRS-PIPE-*, SRS-SRT-*), the
configuration (SRS-CFG-*), the control API's status (SRS-CTL-*), the list-mode sink (SRS-OUT-*).

### Software items and safety class

Changed: processing (the table and the monitor), pipeline (decode and sort), config (the file and
the settings), service (loading, checks, status) and output (the metadata), all class B. No new
item, no class change, no change of segregation. The procedure runs outside the product, on the
calibration side, and is qualified as a tool (TL-29).

### Risk

New hazard H-11 (a wrong calibration table is applied), refining HZ-3, with controls RC-35 (the
server refuses a damaged, out-of-limits, foreign or expired table), RC-36 (the procedure's
acceptance criteria), RC-37 (the photopeak monitor) and RC-38 (the run names its table). Residual:
a table that passes and is wrong because of an input that no criterion checks (the sensor's
saturation energy, the source's position), found by the daily quality control.

### SOUP

No new library in the product. The procedure uses numpy, which the book's figure tools already
used; it is listed with the tool (TL-29). CI installs `python3-numpy`.

### Interfaces and data formats

New data format: the calibration table, schema 1.0. Changed: the acquisition configuration
(schema 1.4: `calibration`), the control API (2.4: status field `calibration`), the run record
and the list-mode metadata (`calibration`). Older configurations are read as before and run
without a table (the identity).

### Documents

ADR 0021 (new) and the ADR index; the calibration table format, version 1 (new); the SRS, version
15; the trace matrix; the risk file (H-11, RC-35 to RC-38); the architecture description, version
12; the configuration schema; the software items; the tool list (TL-29); the design file; the
CHANGELOG.

### Regulatory

The intended use does not change. A calibration procedure and its acceptance criteria are part
of the device's documentation for service and installation (assumption: confirm with team how
your organization releases procedures).

## Verification

Unit tests of the table (Calibration.*, PhotopeakMonitor.AveragesThePhotopeakOfEachBlockOnly), the
file and the service (CalibrationFile.*, CalibrationService.*, CalibrationConfig.*), the pipeline
(Pipeline.CalibratesEverySingleAndTheCorrectionMakesNoneLate,
Pipeline.MonitorsThePhotopeakOfTheCalibratedSingles), the sink
(ListModeSink.NamesTheCalibrationTableInTheFilesAndTheRunRecord) and the simulator; the tool tests
`tools.calib`; the measurements in `measurements/ch26/`, which include the server loading a table
the procedure wrote; all presets of `ci/run_all.sh` and the static analysis.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: a new hazard with four controls,
changes inside existing class B items, a new data format and a new tool with its qualification.
