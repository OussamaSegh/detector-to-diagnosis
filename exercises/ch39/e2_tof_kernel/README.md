# Exercise 39.2 (M): The TOF kernel

**Goal.** Write the weights with which a projector with time of flight spreads a point on a line
over the line's TOF bins, and check them against a simulation of the timing error.

**Time.** 2 hours.

**What to write** (`kernel.py`):
- `sigma_mm(ctr_fwhm_ps)`: the standard deviation, along the line, of the position that a timing
  error of this FWHM gives (the coincidence time resolution, a Gaussian).
- `bin_edges_mm(bins, width_ps)`: the `bins + 1` edges along the line of the histogrammer's TOF
  bins (Exercise 39.1), from endpoint a towards b.
- `probabilities(position_mm, edges_mm, ctr_fwhm_ps)`: for a point at `position_mm` along the line,
  the probability that its measured position falls in each bin.

**Starter.** `starter/kernel.py` converts picoseconds to millimeters with c instead of c / 2 and
takes the Gaussian's density at each bin's center times the bin's width.

**Acceptance** (`tests/test_kernel.py`):
- A resolution of 300 ps FWHM is a standard deviation of 19.1 mm along the line.
- For a point well inside the bins, the probabilities add up to 1 to 1e-12, whatever the bins'
  width; a point at the middle gives symmetric probabilities.
- With bins of 300 ps and a resolution of 100 ps (bins wider than the kernel), a point at the
  middle of a bin puts 99.98% in it.
- 200,000 simulated timing errors fall in the bins as the probabilities say (chi2 per bin below 2).

**Then, by hand.**
1. Why does the projector integrate the Gaussian over each bin instead of sampling it at the bin's
   center, and when does the difference matter?
2. MiniDAQ uses bins of 100 ps with a resolution of 300 ps. What would bins of 20 ps cost, and what
   would they gain?
3. A real scanner's timing error is not quite Gaussian: it has tails. What happens to an image
   reconstructed with a Gaussian kernel that is too narrow?
