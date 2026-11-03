# 0025. Image quality measured by figures of merit after NEMA NU 2, with fixed methods and limits from repeatability

Date: 2026-11-03
Status: Accepted

## Context

Chapter 28's reconstruction gives an image, and its tests show that the algorithm does what its
model says. They do not say how good the image is. A specification, an acceptance test after an
installation or an update, and a weekly quality check all need numbers for that: how sharp
(spatial resolution), how faithful the contrast of small hot objects (contrast recovery), and how
noisy the background (background variability). Each number depends on choices that are easy to
leave unstated: the reconstruction and its iterations, the post-filter, the pixel size, how a
width is read off a profile, and which pixels a region of interest holds. The same scanner gave
a radial FWHM of 0.76 mm or 1.90 mm at 10 mm from the axis depending on the pixel alone, and the
same image a contrast recovery of 0.99 or 1.29 for the 12 mm rod depending on the region
(measurements/ch30). Three questions:

- which methods to use, and from where;
- which reconstruction measures the resolution;
- where the acceptance limits come from.

## Options

1. **Methods of our own**, chosen for MiniDAQ. Free to fit the scanner, but no one outside can
   compare the numbers with another scanner's or with a datasheet.
2. **NEMA NU 2's methods, adapted to 2D.** The standard by which PET scanners are specified:
   point sources reconstructed by FBP for the resolution, with the width from a parabolic peak and
   linear interpolation; hot spheres in a warm background with background regions of each
   sphere's size for contrast and variability (verify: the edition the scanner's specification
   cites). MiniDAQ's reconstruction is 2D, so the spheres become rods and the slices one.
3. **Task-based measures** (a model observer's detectability, for example). Closer to what a
   reader of the image needs, but more parameters to agree on and not what a specification or an
   acceptance test quotes today.

## Decision

Option 2, with every choice an argument that a test or a protocol fixes (`tools/recon/quality.py`,
`tools/recon/fbp.py`):

- A width: the peak by the parabola through the highest sample and its two neighbors, each side
  linearly interpolated, refused if the profile does not fall below the level on both sides
  (SRS-IQ-001). Pixels at most a third of the expected FWHM, and the pixel stated with the result.
- The resolution by FBP with an unwindowed ramp filter and the arc correction (SRS-IQ-002): FBP has
  no iteration number, filter or count dependence to choose. OSEM's width of the same point is
  reported beside it, as the reconstruction's and not the scanner's.
- Contrast recovery from the hot object's whole region; background variability as the spread of
  the means of twelve regions of the object's size, placed by a fixed rule (SRS-IQ-003).
- One reconstruction protocol (OSEM 4 x 8, 2 mm pixels, 4 mm Gaussian), and acceptance limits for
  it that six independent realizations show a correct system meets with room (SRS-IQ-004). A
  weekly check compares each result with limits from the acceptance baseline, not from the
  results under review, and looks for runs on one side of the baseline's mean (Exercise 30.3).

## Consequences

### Positive

- The numbers can be compared with other scanners' and repeated by someone who reads the protocol.
- A change to the reconstruction, its corrections or the protocol that degrades the images shows
  as a figure of merit outside its limits, which RC-44 relies on.
- The methods have tests with known answers; the exercises show the usual mistakes failing them.

### Negative

- 2D, simulated, and without what NEMA NU 2 also measures (sensitivity, count rate performance and
  scatter fraction, the accuracy of the corrections, a lung insert, several slices).
- MiniDAQ's radial bins (1.28 mm at the center) are as wide as its intrinsic resolution there, so
  FBP's radial width near the axis depends on the pixel and on where the point falls among the bins
  (0.76 to 1.35 mm): a central-resolution figure for MiniDAQ is a range, not a number.
- Six realizations are few: the 95% interval of a true standard deviation is about 0.62 to 2.45
  times one estimated from six results.
- The limits are book-level numbers (assumption: confirm with team the acceptance values of the
  scanner's image quality specification).
