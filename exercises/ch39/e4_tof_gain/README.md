# Exercise 39.4 (M): How much time of flight should gain, and where

**Goal.** Chapter 39 measured a gain in background variability of 1.69 at 300 ps where the usual
estimate, sqrt(D / dx), says 2.11, and suggested that regions away from the center gain less. Put a
number on that: the estimate at every point of a uniform cylinder, from the chords of the lines
through it, and for the measurement's own 15 regions.

**Time.** 1 hour.

**Starter.** `starter/gain.py`, with `localization_mm(ctr_ps)`, `chord_mm(r, theta, radius)`,
`gain(r, radius, ctr_ps)` and `region_gain(points, radius, ctr_ps)`. It converts the resolution
with c instead of c / 2, takes the diameter as every chord, and averages the regions' gains.

**Acceptance** (`tests/test_gain.py`, run by `ctest --test-dir build/debug -R ch39/e4`), on a
cylinder of radius 100 mm:
- 300 ps localize to 44.969 mm; a resolution of 0 or less is refused.
- Chords: 200 mm through the center or along the radius; 160 mm across the radius at 60 mm; a
  point outside is refused.
- At the center the gain is sqrt(200 / dx): 2.109 at 300 ps, 1.634 at 500 ps.
- It falls away from the center: 2.022 at 55 mm.
- A cylinder of radius 10 mm, all of whose chords are shorter than dx, gains exactly 1.
- Regions add their variances; the 15 regions of `measurements/ch39/tof.py` give 2.056 at 300 ps.

**Then, by hand.**
1. How much of the gap between 2.11 and the measured 1.69 does the position of the regions
   explain? And at 500 ps, where the measurement found 1.11?
2. The regions are 16 mm across and the localization 45 mm. What does the estimate assume about the
   scale at which the noise is measured, and what does that predict for a measure at a smaller
   scale, such as the unfiltered pixel?
3. Which number goes into a design document, the estimate or the measurement, and what would you
   write next to it?

**Hints.** Average over angles in (0, pi), at the middle of equal steps. The variance is
proportional to the length the counts spread over: D without time of flight, min(D, dx) with it.
For regions, average 1 / gain^2 and take one over its square root.
