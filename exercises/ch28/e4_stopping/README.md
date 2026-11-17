# Exercise 28.4 (M): When to stop OSEM, from a noise target

**Goal.** The number of iterations and subsets is a setting of the reconstruction, validated with
it. Choose it the way the chapter does: run OSEM iteration by iteration, measure the noise of a
uniform region after each one, and stop at the last iteration that is still within a noise
target. Refuse subsets too small to be fair, and a target the first iteration already passes.

**Time.** 1 hour.

**Starter.** `starter/stopping.py`, with `background_noise(x, background)` and
`stop(y, projector, mult, add, count, target, background, max_iterations=100)`, which returns
`(iterations, image, noise)`. The OSEM of Exercise 28.3 is given in `tests/ordered.py`: a call
with `iterations=1` and `x0` continues a reconstruction by one iteration. The starter measures the
noise over the whole image, stops at the first iteration at or above the target, and checks
nothing.

**Acceptance** (`tests/test_stopping.py`, run by `ctest --test-dir build/debug -R ch28/e4`), on a
disc with a hot rod, 36 views, Poisson counts:
- With 4 subsets and a target of 20%, the image is that of the returned number of iterations, its
  background noise is at most 20%, and one more iteration passes 20%.
- The noise returned is the coefficient of variation over the background mask.
- With 2, 3 and 6 subsets, the stop is within one iteration's updates of MLEM's, and the contrast
  of the rod within 0.03 of MLEM's at its stop.
- 12 subsets (3 views each) and 0 subsets raise `ValueError`.
- A target of 5% with 6 subsets, which the first iteration passes, raises `ValueError`.

**Then, by hand.**
1. Where did the starter stop, for every number of subsets, and why? What does the whole image's
   CoV measure that the background's does not?
2. With 6 subsets the stop has 18 updates, against 24 for MLEM and for 2, 3 and 4 subsets. Why,
   and what would a target of 25% give?
3. Why 6 views as the smallest subset here, and would it be the same number for MiniDAQ's 192
   views? Compare with section 6 of `measurements/ch28/reconstruct.txt`.

**Hints.** The noise of the first iterations is not the noise of the data but the image still
taking shape; past them it grows with every update. `ordered.osem(y, p, mult, add, 1, count,
x0=x)` with `x0=None` starts from ones.
