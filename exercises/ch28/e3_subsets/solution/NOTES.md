# Exercise 28.3: notes on the solution

**The two mistakes.**

- *The sensitivity belongs to the subset.* Each update divides the backprojected ratio over the
  subset's views by how much each pixel contributes to those views: the backprojection of `mult`
  over the same views. The starter used the full sensitivity divided by 5, which is right only
  if every subset has as many views and the same factors. Here the first subset has 8 views and
  the others 7, and `mult` changes from view to view. The true image was not a fixed point of
  the starter's update: it moved by up to 0.41 in 3 iterations.
- *A subset should span the half turn.* Five consecutive blocks of about 36 degrees each tell
  the image about one range of angles at a time, so each update pulls it toward a picture that
  fits only that range. Every fifth view gives each subset the whole half turn, and five
  updates per iteration do nearly the work of five MLEM iterations.

**The uneven subsets** (Then, by hand, 1). With interleaved subsets, the per-subset
sensitivities summed to 1.152, 0.968, 0.963, 0.954 and 0.963 times the full one over 5. The
starter's shortcut then over-corrects in the updates of the large subset and under-corrects in
the others, and the errors do not cancel: with the shortcut alone (interleaved subsets), the image
after 4 iterations was 3.3% rms from MLEM's and held 3.7% less activity. For consecutive blocks
the sums ranged from 0.557 to 1.405, and with both mistakes the image was 21% rms away, with 22%
more activity.

**The order** (2). Consecutive blocks with their own sensitivity were 3.6% rms away from MLEM
after 4 iterations, against 0.39% for interleaved subsets. Each update is right on its own, but
consecutive blocks change the image in one direction and then the next, and the iteration ends
on the last block's view of the object. Interleaving makes successive updates nearly
independent of each other, which is what lets 20 updates do the work of 20 MLEM iterations.

**MiniDAQ** (3). 192 views in 8 subsets is 24 views per subset, every eighth view, 7.5 degrees
apart. One view per subset would be the extreme: each update would fit the image to a single
projection, the noise of that projection would go straight into the image, and the iterations
would not converge to the maximum-likelihood image but wander around it. With noise, OSEM does
not converge to the MLEM solution in general; it approaches it while the subsets are each a fair
sample of the data, which is why the number of subsets is a setting to validate (assumption:
confirm with team which subset counts your reconstruction is validated for).
