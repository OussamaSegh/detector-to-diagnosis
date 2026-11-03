# CR-0014: The reconstruction tool

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | Chapter 27 left the corrections of every bin and no image: the team needs a reconstruction to check the corrections end to end and to measure image quality (Chapter 30), and a reconstruction whose model differs from the data gives a plausible wrong image (hazard H-13, new) |
| Decision | approved, 2026-11-03, software lead and risk manager |
| Commits | 0da9ed8, 59619b0 and the commit that adds this record |

## Description

`tools/recon` gains the reconstruction (ADR 0023): `project.bin_lines` gives each sinogram bin's
line, at its own normal angle and distance from the axis, for a stated radius of the lines;
`project.Projector` is Joseph's projector, matrix-free, with its backprojection the exact
adjoint; `mlem.osem` runs MLEM and OSEM with interleaved subsets and the corrections of Chapter 27
in the model, `ybar = m A x + b`; `chain` applies the corrections of Chapter 27 to whole runs. The
reconstruction is a new tool, TL-31 (class T3), in the package of TL-30.

## Reason

An image is what the corrections are for, and the only end-to-end check of them. The ways a
reconstruction goes wrong without an error (a backprojector that is not the adjoint, lines at
the wrong radius, pre-corrected data, gaps read as zero counts) each give an image that looks
right (H-13).

## Impact analysis

### Requirements

New: SRS-REC-001 to SRS-REC-003 (SRS version 17). No requirement changed.

### Software items and safety class

None: the reconstruction runs outside the product and is qualified as a tool (TL-31). No
product item, class or segregation changes.

### Risk

New hazard H-13 (a reconstruction whose model differs from the measurement), with controls RC-41
(the projector's lines and its adjoint) and RC-42 (the corrections in the model, unmeasured bins
without weight, subsets with their own sensitivity). Residual: whether the model fits the
scanner, found by the image-quality measurements of Chapter 30.

### SOUP

No new library. The tool uses numpy, as `tools/calib` and the corrections do. The C++ projector
of Chapter 29 will add pybind11 to the tools, with its own SOUP entry.

### Interfaces and data formats

None. The tool reads the files and the run record of Chapter 27.

### Documents

ADR 0023 (new) and the ADR index; the SRS, version 17; the trace matrix; the risk file (H-13,
RC-41, RC-42); the architecture description, version 14; the tool list (TL-31); the design file;
the CHANGELOG.

### Regulatory

The intended use does not change: MiniDAQ acquires, and the image is made by a tool. Which
reconstruction a product uses, with which settings, is part of the image chain's validation
(assumption: confirm with team where your organization documents its reconstruction).

## Verification

The tool tests `tools.recon`, among them Projection.test_the_backprojector_is_the_adjoint,
Projection.test_an_off_center_object_lies_on_its_sinusoid,
Reconstruction.test_mlem_never_lowers_the_likelihood,
Reconstruction.test_unmeasured_bins_take_no_part and
Reconstruction.test_subsets_must_cover_the_views; the measurements in
`measurements/ch28/`; Exercises 28.1 to 28.3, whose starters each make one of H-13's mistakes
and fail; the static analysis.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: a new tool with its
qualification, a new hazard with two controls, and no change to the product.
