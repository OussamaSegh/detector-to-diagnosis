# 0038. Time of flight in the projector, and only on a time base the run says held

Date: 2026-11-16
Status: Accepted

## Context

The difference of the two photons' arrival times says where along its line of response an
annihilation happened: c tau / 2 from the line's middle, 15 mm for every 100 ps. A scanner whose
coincidence time resolution is a few hundred picoseconds narrows each event from the whole chord
through the patient to a Gaussian of a few centimeters, and the image's noise falls by about the
square root of the ratio (Chapter 39).

MiniDAQ already records what time of flight needs. Each list-mode record holds `dt_ps`, the later
single's time less the earlier's, signed, to the picosecond (MDQ-L1, Chapter 12), and the
histogrammer bins tau = t_a - t_b of each line into TOF bins. What was missing was everything
after: the reconstruction tool's projector (Chapters 28 and 29) spreads each line's counts over
its whole length, and nothing stops a run whose block clocks moved (Chapter 38) from being
reconstructed as if they had not.

## Options

1. **TOF in list mode only**: reconstruct event by event from the list-mode file, with a kernel
   per event. Exact, and the natural form for TOF; it needs a list-mode reconstruction, a second
   algorithm next to the sinogram OSEM of Chapter 28, with its own tests.
2. **TOF sinograms**: the histogrammer's TOF bins as a third dimension of the sinogram, and a
   projector that weights each step of a line by the probability of each TOF bin. The OSEM, the
   subsets and the corrections stay as they are; the projector changes, in both its numpy reference
   and its C++ implementation.
3. **Leave TOF out** and document it. The book would explain what MiniDAQ cannot use.

## Decision

Option 2. The projector is the one place that changes; the OSEM of Chapter 28 works on any shape
of sinogram whose first axis is the view, and the comparison of the numpy and C++ projectors
(RC-43) extends to TOF unchanged.

- The kernel is the Gaussian of the stated resolution (FWHM, from the timing calibration)
  integrated over each TOF bin with erf. Each step of Joseph's walk has a position along its line;
  forward and back use the same kernel, so the adjoint holds as before.
- The sign is fixed once and tested end to end: endpoint a of a bin (lor_bin()) lies at negative
  positions along the direction (-sin phi, cos phi) of the bin's own angle, and tau = t_a - t_b
  puts the event at c tau / 2. A test simulates an off-center point source, bins it in the
  histogrammer and in Python, and checks that the TOF profile of each line through it is centered
  on the point.
- A reconstruction with TOF reads the run record first and refuses a run whose time base monitor
  was at alarm in any interval, whose board clock lost its lock, or which has no verdict at all
  (a run of a server before 2.0). The same run reconstructs without TOF: a block clock off by
  400 ps loses a few coincidences at the window's edge without TOF, and moves every event of the
  block by 60 mm with it.

## Consequences

### Positive

- The noise of a TOF image falls with the resolution, measured in `measurements/ch39/`.
- The list-mode format and the histogrammer do not change: the data written since 1.0 can be
  reconstructed with TOF.
- RC-55 joins H-13's controls; the time base verdict of Chapter 38 gets a consumer that acts on it.

### Negative

- A TOF projection costs a kernel per step and K times the memory per sinogram; measured in
  `measurements/ch39/`. The numpy reference is slow (an erf per edge and step); the C++ projector
  is the one to use for real data.
- The numpy erf is an approximation within 1.5e-7 (numpy has none, and scipy is not a dependency
  of the tool); the comparison with the C++ projector allows for it.
- A Gaussian kernel of one width for every line: the resolution of a real scanner varies with
  the crystal pair, the energy and the count rate (assumption: confirm with team how the timing
  calibration reports it). A run must be reconstructed with the resolution it was acquired with.
