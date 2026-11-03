# Exercise 28.1 (M): A backprojector that is the adjoint of its projector

**Goal.** Write the backprojection and the sensitivity image that MLEM needs, for a projector
you are given, so that the pair is exactly a matrix and its transpose. This is the property that
`tools/recon/project.py` checks for Joseph's projector, on a geometry small enough to reason
about by hand.

**Time.** 60 minutes.

**Starter.** `starter/adjoint.py` runs. `forward` is given and correct: each pixel's value goes
to the two radial bins nearest to its `s = x cos(phi) + y sin(phi)`, split linearly. `back`
gives each pixel, in every view, the value of the bin nearest to its `s`. `sensitivity` returns
the number of views for every pixel.

**Acceptance** (`tests/test_adjoint.py`, an image of 32 x 32 unit pixels, 36 views over 180
degrees, 41 radial bins of width 1):
- The dot-product test: `<forward(x), y> = <x, back(y)>` to 1e-12 relative, for random `x` and
  `y`.
- `sensitivity(g, mult)` equals `back(mult)` for any multiplicative factors `mult`, and a corner
  pixel, whose `s` leaves the bins in some views, has a smaller sensitivity than the center.
- MLEM on noiseless data of a disc of radius 10: the likelihood never decreases over 30
  iterations, the inside of the disc comes out within 0.03 of 1, and outside it below 0.05.
- MLEM started at the true image, with activity in every pixel, stays there to 1e-9.

**Then, by hand.**
1. The starter's `back` is a fine backprojection to look at. By how much does it fail the
   dot-product test, and why does the MLEM test of the disc still pass with it?
2. How much of its weight does pixel (0, 0) lose outside the bins, and what does the starter's
   MLEM do to it in one iteration from the truth?
3. In `tools/recon/mlem.py` the sensitivity is `back(m)` with `m` the normalization times the
   attenuation times the live fraction. Why is it computed per subset in OSEM, not once?
   Answer in `NOTES.md`.

**Hints.** Write `forward` as `y = A x` and read off what `A` is for one view: a column of `A`
(one pixel) has two entries, in bins `lo` and `lo + 1`, with weights `1 - frac` and `frac`. The
transpose gathers from the same two bins with the same weights. The sensitivity is what the
transpose gives for data that is all ones, weighted by `mult`.
