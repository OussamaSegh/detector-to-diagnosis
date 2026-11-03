# CR-0015: The reconstruction's projector in C++, with Python bindings

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | the numpy projector of Chapter 28 takes nearly all of the reconstruction's time and keeps 89 MB of weights for one 2D image; a 3D reconstruction would not fit (ADR 0024) |
| Decision | approved, 2026-11-03, software lead and risk manager; pybind11 approved as a new dependency by the project owner on 2026-11-03 |
| Commits | a6d37fc and the commit that adds this record |

## Description

A C++20 library, `recon/` (`recon::JosephProjector`), computes the projector of
`tools/recon/project.py` with its weights on the fly and its lines shared between threads; the
backprojection adds into an image per thread. The module `recon_cpp`, built with pybind11
3.1.0 (pinned by commit), exposes it to Python with the numpy projector's interface, checks the
shape of every array, converts other dtypes and memory layouts, and releases the GIL while it
computes. `project.CppProjector` wraps the module. The numpy projector stays the reference.

## Reason

Speed and memory, for the reconstruction now and for 3D later: one projection takes 34 ms on
one thread and 14 ms on four, against 57 ms in numpy, and the C++ projector keeps no weights
(`measurements/ch29`).

## Impact analysis

### Requirements

New: SRS-REC-004 to SRS-REC-006 (SRS version 18). No requirement changed.

### Software items and safety class

None of the product's: `recon/` is part of the reconstruction tool (TL-31), outside the shipped
programs, and no product item links it.

### Risk

H-13 gains a cause (a second implementation that differs, reads an array in the wrong layout or
loses lines between threads) and a control, RC-43. Residual unchanged.

### SOUP

New: pybind11 3.1.0, BSD-3-Clause, used only to build the tool's module (SOUP list version 11,
section 2; the SBOM's known dependencies; tool TL-32). The build needs the Python headers.

### Interfaces and data formats

None. The module is an interface inside the tool.

### Documents

ADR 0024 (new) and the ADR index; the SRS, version 18; the trace matrix; the risk file (RC-43);
the architecture description, version 15; the SOUP list, version 11; the tool list (TL-31,
TL-32); the CI workflows (`python3-dev`); the static analysis and the trace matrix cover
`recon/`; the CHANGELOG; "How to use this book".

### Regulatory

The intended use does not change.

## Verification

The C++ tests JosephProjector.BackIsTheAdjointOfForward,
JosephProjector.TheThreadsDoNotChangeTheResult and JosephProjector.RefusesWhatDoesNotFit, in
every preset and under ThreadSanitizer; the Python
tests of `tools.recon_cpp`, among them SameAsNumpy.test_the_projections_agree_line_by_line and
TheBoundary.test_converts_other_dtypes_and_layouts, with every test of the numpy projector run on
the C++ one; the measurement in `measurements/ch29/`; Exercises 29.1 to 29.3; the static analysis,
now over `recon/src` too.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: a second implementation of a
tool's projector with its comparison to the reference, a new build-time SOUP item, and no change
to the product.
