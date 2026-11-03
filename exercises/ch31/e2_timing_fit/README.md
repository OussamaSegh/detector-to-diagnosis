# Exercise 31.2 (M): A timing fit you can trust at low counts

**Goal.** Fit the timing peak of a coincidence histogram (a Gaussian on a flat background,
integrated over each bin) by maximum likelihood for Poisson counts, and give each parameter a
standard error that is the real spread of the estimate. Only numpy: no SciPy.

**Time.** 2 hours.

**Starter.** `starter/timing_fit.py` runs and fits a strong peak well. It fits by least squares
with each bin weighted by its own count, the weighting `curve_fit` uses when it is given
`sigma=np.sqrt(counts)`, and takes its errors from that fit.

**Acceptance** (`tests/test_timing_fit.py`):
- A peak of 100,000 counts: FWHM, center and area within four standard errors of the truth.
- A peak of 300 counts on a background of 0.01 per ps (most bins hold zero or one count): the mean
  area over 300 histograms within 3% of the truth.
- Over 300 histograms of 3,000 counts, (FWHM - truth) / error has a standard deviation within 15%
  of 1 and a mean within 0.2 of 0.
- Fewer than 50 counts: `ValueError`.

**Then, by hand.**
1. Plot the starter's 300 weak-peak areas. Is the bias a shift of every fit, or a few fits that
   went wrong? What does the weight of an empty bin do?
2. Show that at the minimum of the Poisson deviance the fitted total equals the observed total
   when the model has a free overall scale. Which parameter plays that role here?
3. Why are the errors the square roots of the diagonal of the inverse Fisher matrix, and not
   one over the square roots of its diagonal? Answer in `NOTES.md`.

**Hints.** The deviance is 2 sum(mu - n + n ln(n/mu)), with the last term 0 where n = 0. Its
gradient is -2 J^T (n/mu - 1) and its expected curvature 2 J^T diag(1/mu) J, where J is the
derivative of the expected counts with respect to the parameters. Halve a step that does not
lower the deviance; keep the background at or above zero.
