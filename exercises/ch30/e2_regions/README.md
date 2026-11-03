# Exercise 30.2 (S): Contrast and noise from regions of interest

**Goal.** Compute a hot region's contrast recovery coefficient (CRC) and the background
variability of an image the way NEMA NU 2 describes it for its image quality phantom: the
variability of the means of several background regions of one size, not of the pixels.

**Time.** 30 minutes.

**Starter.** `starter/regions.py` runs. `contrast_recovery` divides the measured ratio by the true
one. `background_variability` pools the pixels of all the regions and takes their standard
deviation.

**Acceptance** (`tests/test_regions.py`, 128 x 128 pixels of 1 mm, twelve regions on a circle of
40 mm):
- The true contrast gives a CRC of 1 and no contrast a CRC of 0, for any background level.
- Regions each uniform at a known level give the mean of the levels and their sample standard
  deviation (K - 1) over the mean, exactly.
- With independent pixel noise of 10%, the variability of regions of 3 and 6 mm radius is within
  10% of 10% over the square root of each region's pixels, and the smaller regions vary about
  twice as much.

**Then, by hand.**
1. What did the starter give for the regions of 3 and 6 mm, and why is that number the same for
   both?
2. The starter's CRC is 0.25 for an image with no contrast at all. What does a CRC computed that
   way measure?
3. In section 3 of `measurements/ch30/quality.txt` the variability of the 5 mm regions is two to
   four times that of the 12 mm regions in the same image. Is the 5 mm rod's image noisier?
   Answer in `NOTES.md`.

**Hints.** First the mean of each region, then the statistics of those twelve means.
