# CR-0016: Image quality figures of merit and a reconstruction protocol with limits

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | H-13's residual risk: the reconstruction's tests verify the algorithm against its model, not the quality of its images; no protocol or acceptance limits existed (ADR 0025) |
| Decision | approved, 2026-11-03, software lead and risk manager |
| Commits | fa6b0d6 and the commit that adds this record |

## Description

The reconstruction tool gains filtered backprojection (`tools/recon/fbp.py`) and the figures of
merit of an image (`tools/recon/quality.py`): the FWHM and FWTM of a profile from a parabolic peak
and linear interpolation, profiles through a point, regions of interest, the contrast recovery
coefficient, and the background variability from the means of regions placed by a fixed rule.
`measurements/ch30/quality.py` measures MiniDAQ's images with them, after the methods of NEMA NU 2
in 2D, and SRS-IQ-004 sets a reconstruction protocol with acceptance limits.

## Reason

A specification, an acceptance test and a recurring check of image quality need numbers, and the
numbers depend on choices (reconstruction, iterations, filter, pixel, regions) that must be fixed
to be comparable. The same point's width changed from 0.76 to 1.90 mm with the pixel alone, and
the same image's contrast from 0.99 to 1.29 with the region alone (`measurements/ch30`).

## Impact analysis

### Requirements

New: SRS-IQ-001 to SRS-IQ-004 (SRS version 19); SRS-IQ-004 is verified by measurement, with its
evidence in the SRS's section 3. No requirement changed.

### Software items and safety class

None of the product's: the new code is part of the reconstruction tool (TL-31), outside the
shipped programs.

### Risk

H-13 gains a control, RC-44 (the protocol measured with phantoms by tested methods and accepted
against limits), and its residual risk names what the control does not cover: 3D, real phantoms
and the clinical protocols. No new hazard.

### SOUP

None.

### Interfaces and data formats

None.

### Documents

ADR 0025 (new) and the ADR index; the SRS, version 19; the trace matrix; the risk file (RC-44,
H-13's residual); the architecture description, version 16; the tool list (TL-31); the CHANGELOG.

### Regulatory

The intended use does not change. The 2D adaptation is not a NEMA NU 2 measurement and is not
reported as one.

## Verification

The tests of `tools.recon` and `tools.recon_cpp`, among them
ImageQuality.test_a_width_is_interpolated_from_a_parabolic_peak,
ImageQuality.test_fbp_gives_a_disc_its_value_and_a_point_its_place,
ImageQuality.test_background_variability_is_the_spread_of_region_means and
ImageQuality.test_background_regions_are_placed_the_same_way_and_kept_out, run on the numpy and the
C++ projector; the measurement in `measurements/ch30/`, whose six realizations meet SRS-IQ-004;
Exercises 30.1 to 30.3, whose starters fail.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: figures of merit in a tool, a
measured protocol with book-level limits (assumption: confirm with team the acceptance values of
the scanner's image quality specification), and no change to the product.
