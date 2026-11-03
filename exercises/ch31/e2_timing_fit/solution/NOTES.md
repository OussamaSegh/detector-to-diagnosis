# Exercise 31.2: notes

The starter's area over 300 weak peaks averaged 394, 31% above the truth of 300. Two biases
are mixed in that number. Four of the 300 fits ran away, with a "peak" more than 1,000 ps wide
that absorbs the background; they carry the mean up. The other 296 fits average 270, 10% below
the truth: the classic bias of weighting by the observed counts, which trusts a bin that
fluctuated low (small count, small sigma) more than one that fluctuated high, so the curve is
pulled down. An empty bin gets the weight of a bin with one count, which makes the runaways
possible. The median FWHM of the starter is 281 ps for a truth of 300.

The solution's mean area over the same 300 histograms is 300.6 and its mean FWHM 298.5 ps.

By hand:

1. Both: a few fits that went wrong (four of 300) push the mean up, and the rest are shifted down
   by about 10%.
2. The derivative of the deviance with respect to an overall scale s of mu (mu = s m) is
   2 sum(m - n m / mu) = 2 (sum mu - sum n) / s. It is zero at the minimum, so the fitted total
   equals the observed total. Here the area and the background together set the total: at the
   minimum the expected counts summed over the fitted bins equal the observed counts.
3. The covariance of the estimates is the inverse of the Fisher matrix. The square root of a
   diagonal element of the inverse includes the correlations with the other parameters; one over
   the square root of a diagonal element of the matrix itself is the error with every other
   parameter held fixed, which is smaller when the parameters are correlated (area and
   background are).
