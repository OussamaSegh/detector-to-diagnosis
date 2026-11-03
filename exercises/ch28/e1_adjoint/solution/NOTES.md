# Exercise 28.1: notes on the solution

**The two mistakes.**

- *A backprojection that looks right is not the adjoint.* The starter took the nearest bin. The
  projector split each pixel between two bins, so the transpose must gather from the same two
  bins with the same weights: linear interpolation of the sinogram at the pixel's `s`. The
  nearest bin differs from it by 4.2% rms of the mean for a random sinogram, and the dot
  product came out 1.0025 instead of 1. The solution uses `_splat` in both directions, so the
  pair cannot drift apart when one of them changes.
- *The sensitivity is a backprojection, not a count of views.* A pixel contributes to a view
  only through the bins its weights land in. Near the corners `s` reaches 21.9, past the last
  bin at 20, and part of the weight falls outside. The starter divided every pixel by 36; the
  solution backprojects the multiplicative factors, 27.8 for pixel (0, 0) and 36 at the center.

**The disc** (Then, by hand, 1). The 0.25% mismatch in the dot product is small, and the disc
lies well inside the field, where the constant 36 is right. MLEM converged to within 0.002 of
the true value inside the disc with either backprojector. A test that only looks at the middle
of the image would not have caught either mistake, which is why the acceptance includes the
dot-product test and a fixed point with activity in the corners.

**The corner** (2). Pixel (0, 0) keeps 27.8 of its 36 views' weight. Started at the truth, the
ratio of measured to expected counts is 1 in every bin, the backprojection of the ratio is 27.8,
and the starter divides by 36: the pixel drops to 0.77 of its value in one iteration, 0.36 after
5 and 0.15 after 30. The solution divides by 27.8 and stays at the truth to rounding. In the
scanner the same thing happens wherever `m` is not uniform: in the gaps between blocks, behind
the bed, in a dead crystal's lines.

**Per subset** (3). An OSEM update uses only the views of one subset, so its denominator must
be the backprojection of `m` over those views. With MiniDAQ's interleaved subsets the views of a
subset are spread over all angles and the per-subset sensitivities are close to the full one
over the number of subsets, but not equal: `m` differs from view to view through the gaps and
the attenuation. Exercise 28.3 measures what the shortcut costs.
