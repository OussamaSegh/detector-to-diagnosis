# CR-0034: The C++ projector writes into an array the caller gives

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-17, by the software lead |
| Source | roadmap 2.1.0, theme H (Chapter 29: zero-copy exchange of arrays, the cost of the crossing) |
| Decision | approved, 2026-11-21, by the software lead (the author), in writing in the project |
| Commits | the commit that adds this request |

## Description

The reconstruction tool's module `recon_cpp` gains an optional argument `out` for
`Projector.forward` and `Projector.back` (and so for `TofProjector`). When it is given, the
projection is written into that array, the caller's own memory through the buffer protocol, and
the array is returned; when it is not, a new array is returned as before.

`out` is never converted. It is accepted only if it is a NumPy array that is float64,
C-contiguous, writeable and of the result's shape, and does not share memory with the input;
any other is refused with `ValueError` (`TypeError` for an object that is not an array) that
says which of these it is not, and nothing is written. A converted `out` would receive the
projection and be thrown away, leaving the caller's array as it was, without an error.

## Reason

An OSEM loop allocates a new image and a new sinogram for every subset. With `out` it can reuse
one of each, and Chapter 29 can show the buffer protocol at work and measure what the crossing
of the boundary costs: a call, a conversion of the input, an allocation of the output
(`measurements/ch29/crossing.txt`). The rule that an output is never converted is the one
Exercise 29.4 teaches; the module itself must follow it.

## Impact analysis

### Requirements

Added: SRS-REC-009, "The reconstruction tool's compiled projector `recon_cpp` shall write a
projection into an output array the caller gives, without a copy, and refuse, without writing
anything, an output that is not a writeable, C-contiguous float64 NumPy array of the result's
shape or that shares memory with the input." Verified by test. SRS-REC-004 to SRS-REC-006 do not
change: without `out`, the module behaves as before.

### Software items and safety class

None of MiniDAQ's shipped software items changes. The change is in the reconstruction tool
(TL-31), its module `recon/python/recon_cpp.cpp`; the library `recon::JosephProjector` does not
change.

### Risk

H-13 (an image that is not the maximum-likelihood image of the data): one more way for an array
to cross the boundary. The new cause, a projection written into a converted copy and lost, or
into memory the input occupies, is controlled by the refusal above and its tests (RC-43, whose
description gains the output). No new hazard.

### SOUP

None. pybind11 3.1.0 (TL-32) as before; `py::array` and its flags are part of
the API already used.

### Interfaces and data formats

The module's interface gains an optional keyword argument; every existing call is unchanged
(roadmap 2.1.0: compatible additions only). No file format changes.

### Documents

The SRS (SRS-REC-009, a new version); the risk file (RC-43's description); the tool list (TL-31
and TL-32's evidence); Chapter 29 and its measurements; the CHANGELOG.

### Regulatory

The intended use does not change. The reconstruction tool is not part of the shipped device.

## Verification

Tests in `tools/test_recon_cpp.py` (`tools.recon_cpp`):
`TheBoundary.test_writes_into_an_output_the_caller_gives` and
`TheBoundary.test_refuses_an_output_it_cannot_write_in_place`; the projector's other tests, which
run without `out`; `recon.wheel`, which runs them against the installed wheel; `docs.srs`,
`docs.trace`, `docs.changes`; the whole ctest.

## Decision

Approved by the software lead on 2026-11-21, in writing in the project.
