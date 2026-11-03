# CR-0013: The inputs of the corrections in the run record, and the corrections tool

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | design review of the data path after Chapter 26: the run record held the coincidences' counts but not the singles rates, the windows or the window mode that the randoms, dead-time and normalization corrections need, and nothing tied a normalization scan to the runs it corrects (hazard H-12, new) |
| Decision | approved, 2026-11-03, software lead and risk manager |
| Commits | dae3167 and the commit that adds this record |

## Description

The pipeline's decode stage counts, after calibration, the singles in the sorter's energy window
for each crystal and every valid single for each detector block, with the first and last time
(`processing/singles_counter`). At the end of a run the acquisition service writes them into the
run record's new `corrections` object with the sorter's energy window, coincidence window, window
mode and delayed window, and the numbers of prompts and delayeds (`control/corrections_record`;
MDQ-L1 specification, version 3). The corrections tool, `tools/recon`, is a new in-house tool
(TL-30, class T3): it reads the list-mode files and the record, bins the coincidences as
`minidaq_listmode sino` does, computes the normalization, randoms, attenuation, scatter, dead-time
and decay corrections, and refuses a normalization taken with other settings. `minidaq_sim` gains
crystal efficiencies, an extended source for normalization scans and truth sinograms of each kind
of coincidence.

## Reason

Without the singles and the windows a randoms estimate from the singles is impossible and a
dead-time correction has no rate to start from; without the windows and the calibration table in
both records, a normalization measured under other settings corrects a run without an error, and
the image's values and uniformity are wrong (H-12).

## Impact analysis

### Requirements

New: SRS-COR-001 to SRS-COR-003 and SRS-SIM-023 (SRS version 16). Changed: SRS-CAL-007 (wording
only: "of its center", "partners in at least 40 crystals"). Verification repeated: the pipeline
(SRS-PIPE-*), the list-mode sink and the run record (SRS-OUT-*), the simulator (SRS-SIM-*).

### Software items and safety class

Changed: processing (the singles counter), pipeline (the decode stage counts), service (the run
record), all class B. No new item, no class change, no change of segregation. The corrections
tool runs outside the product and is qualified as a tool (TL-30).

### Risk

New hazard H-12 (corrections computed from inputs that do not belong to the data), with controls
RC-39 (the run record carries the corrections' inputs) and RC-40 (the tool refuses a normalization
from other settings). Residual: the models the corrections rest on (the attenuation outline, the
scatter model's shape, the dead-time model's kind), validated with phantoms (Chapter 30).

### SOUP

No new library in the product. The tool uses numpy, as `tools/calib` does.

### Interfaces and data formats

Changed: the run record (`run.corrections`, format 1; MDQ-L1 specification version 3). The
list-mode files, the configuration schema (1.4) and the control API (2.4) do not change. A
reader that does not know `corrections` ignores it.

### Documents

ADR 0022 (new) and the ADR index; the MDQ-L1 specification, version 3; the SRS, version 16; the
trace matrix; the risk file (H-12, RC-39, RC-40); the architecture description, version 13; the
software items and layers; the tool list (TL-30); the design file; the CHANGELOG.

### Regulatory

The intended use does not change. Which corrections the reconstruction applies, and how they are
validated, is part of the image chain's validation (assumption: confirm with team where your
organization documents the reconstruction's inputs).

## Verification

Unit tests of the counter and the record (SinglesCounter.*, CorrectionsRecord.*), the sink
(ListModeSink.WritesRealFilesThroughTheService checks the record) and the simulator
(DetectorSimulator.EachCrystalDetectsWithItsOwnEfficiency); the tool tests `tools.recon`, which
include its binning against `minidaq_listmode sino` bin for bin; the measurements in
`measurements/ch27/`, each correction against the simulator's truth and the counter's cost; all
presets of `ci/run_all.sh` and the static analysis.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: a new hazard with two controls,
changes inside existing class B items, a changed run record and a new tool with its
qualification.
