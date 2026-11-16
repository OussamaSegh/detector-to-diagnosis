# Exercise 38.3: notes

The starter fails all five tests: its offsets put the first block of a group at zero instead of
the mean, it has no uncertainties or chi2, and its answer with noisy pairs is the noise of one
path through the tree, several times that of the fit.

Design choices:

- The normal equations of the weighted fit are L o = r, with L the Laplacian of the graph whose
  edges are the pairs, weighted by 1 / variance. L is singular once per connected group; adding
  J / size over each group (J all ones) makes it invertible and picks the solution with a mean of
  zero, and the inverse less J / size is the covariance. This is how `solve_block_offsets` in C++
  does it, for 72 blocks.
- Groups come from a union-find over the pairs, before the matrix is built, so that the J / size
  terms are per group.
- For thousands of unknowns, such as Chapter 26's crystal delays, a dense inverse is too
  expensive: conjugate gradients on L o = r, as `tools/calib/timing.py` does, need only products
  with L. The covariance is then not available cheaply; for 72 blocks it costs 0.3 ms.
- chi2 per degree of freedom near 1 says that block clocks explain the shifts within their
  variances. A swapped pair of cables, a geometry that changed, or variances that are wrong all
  make it larger; it says that something is wrong, not what.
