# CR-0032: Time of flight in the reconstruction tool

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-16, by the software lead |
| Source | roadmap 2.0.0, theme C (Chapter 39); hazard H-13; the time base verdict of CR-0031, which had no consumer |
| Decision | approved, 2026-11-16, under the software lead's standing delegation of 2026-11-15 |
| Commits | listed when the change is implemented |

## Description

The reconstruction tool (`tools/recon`, tool TL-31) reconstructs with time of flight (ADR 0038).

1. **Projector with TOF** (`tools/recon/project.py` `TofProjector`, the numpy reference, and
   `recon::JosephProjector` with `recon::Tof`, bound as `recon_cpp.TofProjector`). Each step of a
   line is weighted by the probability of each TOF bin for a Gaussian timing error of the stated
   resolution; sinograms are views x radial bins x TOF bins (SRS-REC-007).
2. **TOF bins from list mode** (`tools/recon/sinogram.py` `bin_2d`): the histogrammer's lines,
   TOF bins and sign of tau, every slice added, so that a measurement does not need the 3D TOF
   sinogram files.
3. **Guard** (`tools/recon/chain.py` `check_time_base_for_tof`): a reconstruction with TOF is
   refused for a run whose record has no time base verdict, an interval at alarm, or a board
   clock that lost its lock (SRS-REC-008).

## Reason

The list mode and the histogrammer have carried each event's time difference since 1.0, but the
reconstruction placed every event anywhere along its line. Time of flight lowers the noise of the
image (measured in `measurements/ch39/`). It also makes the image depend on the time base: an
event of a block whose clock moved is displaced along its line, which a reconstruction without
TOF does not do, so the time base verdict of CR-0031 must be read before TOF is used.

## Impact analysis

### Requirements

Added: SRS-REC-007, SRS-REC-008 (SRS version 35). Verification repeated: the tests of the
projectors (C++ and Python, `tools.recon`, `tools.recon_cpp`, `recon_tests`).

### Software items and safety class

None of MiniDAQ's software items changes: the reconstruction tool is a tool (TL-31), validated
by its tests, outside the shipped programs. The library `recon::projector` gains a constructor
and a member; the projection without TOF is unchanged, which the existing tests check.

### Risk

Hazard H-13: its sequence gains the TOF failures (the wrong sign of tau, a run whose block clocks
moved), and RC-55 is a new protective measure for them. The probability after the controls stays
P2. H-02's residual is unchanged: the time base monitor (RC-53) is what RC-55 relies on, and what
it cannot see (a constant offset from the start, a shift below the warning limit) reaches a TOF
image as a displacement along the lines; the timing calibration (Chapter 26) controls the first.

### SOUP

None.

### Interfaces and data formats

None change. The list-mode format, the histogrammer's TOF bins and the run record are read as
they are. The C++ library's interface gains `recon::Tof` and a constructor (additions only), and
the Python module `recon_cpp` gains `TofProjector`.

### Documents

The SRS, version 35 and later; ADR 0038; the risk file (H-13); the trace matrix; Chapter 39; the
CHANGELOG.

### Regulatory

The intended use does not change. The change is in a tool, and adds a protective measure to H-13.

## Verification

Tests: `TofProjector.BackIsTheAdjointOfForward`,
`TofProjector.TheTofBinsAddUpToTheProjectionWithoutTof`,
`TofProjector.APointLiesWhereItsTimeOfFlightSays`, `TofProjector.TheThreadsDoNotChangeTheResult`,
`TofProjector.RefusesATimingThatCannotBe`; in Python `TofProjection`, `TofReconstruction`,
`TofGuard`, `EndToEnd.test_tof_bins_agree_with_the_histogrammer` (`tools.recon`), and
`CppTofProjection`, `CppTofReconstruction`, `TofSameAsNumpy` (`tools.recon_cpp`); `docs.trace`,
`docs.baseline`, `docs.changes`, `docs.risk`; the whole ctest.

## Decision

Approved on 2026-11-16 by the coordinator under the standing delegation that the software lead
gave on 2026-11-15 for the work towards 2.0.0, after reading the impact analysis above.
