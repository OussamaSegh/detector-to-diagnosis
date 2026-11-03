# Exercise 28.2 (M): The corrections in the model

**Goal.** Reconstruct counts whose bins have their own multiplicative factors (normalization,
attenuation, live fraction) and additive ones (randoms, scatter), with the corrections in the
model, `ybar = mult * (A x) + add`, the way `tools/recon/mlem.py` does. See for yourself why the
measured counts must stay untouched.

**Time.** 60 minutes.

**Starter.** `starter/model.py` runs. `reconstruct` corrects the data first, `(y - add) / mult`
with negative values set to 0 and the bins with `mult = 0` set to 0, then runs plain MLEM on the
corrected sinogram with the sensitivity of a perfect scanner. The projector is given in
`tests/projector.py`: the pair of Exercise 28.1.

**Acceptance** (`tests/test_model.py`, an image of 32 x 32 unit pixels, 36 views, 41 radial
bins):
- A disc of radius 12 at 0.1 counts per unit length, `mult = 0.5` and 2 randoms per bin: at most
  1.3 trues per bin. Over 20 noise realizations of 100 iterations, the mean of the disc's inner
  part within 3% of the truth and the mean of a ring outside it below 0.04; the likelihood never
  decreases.
- A disc of radius 15 with every sixth radial bin unmeasured (`mult = 0`, no counts there), 50
  iterations: the inner part within 0.01 of 1 on average with a standard deviation below 0.05,
  and the likelihood never decreasing.
- `reconstruct` does not change the counts it is given.

**Then, by hand.**
1. In the low-count test, how many counts does setting the negative bins to 0 add to the
   corrected sinogram, and where does the starter's image put them?
2. The starter divides by `mult` only where it is not 0 and sets the gaps to 0. What does MLEM
   then believe about the lines in the gaps, and what does the image look like?
3. With the corrections in the model, the solution's image outside the disc is not 0 either.
   Why not, and why does it not mean the model is wrong? Answer in `NOTES.md`.

**Hints.** Change three things: the expected counts, the ratio, and the sensitivity. The
expected counts of a bin are `mult * forward(x) + add`. The backprojected ratio is weighted by
`mult`, because that is the column of the system matrix `mult * A`. The sensitivity is the
backprojection of `mult`, so that a bin with `mult = 0` takes no part in the update at all.
