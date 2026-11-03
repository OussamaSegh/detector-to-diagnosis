# Exercise 30.1 (S): A width that does not depend on the pixels

**Goal.** Measure the full width of a peak at half and at a tenth of its maximum (FWHM, FWTM) the
way NEMA NU 2 describes: the maximum from a parabola through the highest sample and its two
neighbors, and each side interpolated linearly between the samples around the level.

**Time.** 30 minutes.

**Starter.** `starter/width.py` runs. `peak` returns the highest sample. `width` counts the
samples above the level and multiplies by the step.

**Acceptance** (`tests/test_width.py`):
- A profile with straight sides and a symmetric top is measured exactly, at half and at a tenth
  of the maximum, and in mm for any step.
- A Gaussian of 3.5 samples FWHM is measured within 4% (FWHM and FWTM) wherever its center falls
  between samples, and one of 7 samples within 1.5%.
- The peak of a Gaussian centered between two samples is found there, and within 2% of its
  height.
- A profile that does not fall below the level on both sides is refused with `ValueError`.

**Then, by hand.**
1. How far off was the starter's FWHM for the Gaussian of 3.5 samples, and why does it jump as the
   center moves?
2. Why does the parabola matter more for the FWTM than for the FWHM, or the other way around?
3. Section 1 of `measurements/ch30/quality.txt` gives the FBP width of one point at four pixel
   sizes. Which of them meet NEMA's rule of at most a third of the FWHM per pixel? Answer in
   `NOTES.md`.

**Hints.** Walk outward from the highest sample to the first sample at or below the level on each
side; the crossing is between that sample and the one before it.
