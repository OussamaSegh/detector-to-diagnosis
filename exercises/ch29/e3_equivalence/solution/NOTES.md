# Exercise 29.3: notes on the solution

**The mistake.** The starter compared the forward projections of a centered disc. A centered disc
projects to the same profile in every view, and the profile is symmetric in `s`: a projector with
its angles shifted, or with `s` reversed, gives the disc's projection exactly, and the starter
accepted the reversed one with a difference of exactly 0. It never called `back`, so a
backprojector that is not the adjoint (12% off for a random sinogram) passed too. The half-view
shift was refused only by accident: the disc's square pixels make its projection depend a little
on the angle. The solution compares both directions on a random image and a random sinogram,
which have no symmetry for a mistake to hide behind, and checks the shapes first, so that 43
bins are reported as a geometry, not as a crash in the subtraction.

**Accepted and refused** (Then, by hand, 1). Accepted by the starter: `s` reversed, the
nearest-bin backprojector and the other geometry (it raised an error from NumPy instead of an
`AssertionError`). The solution's messages: forward 1.4e-1 for the shifted angles, forward
1.9e-1 for `s` reversed, back 1.2e-1 for the nearest bin, forward 1.0e-4 for the scale.

**rtol** (2). Start from what the two implementations are allowed to differ by: the reference
keeps its weights in float32, about 6e-8 relative per weight, and the sums add a little; the
measurement in `measurements/ch29` found 4e-8 for forward and 5e-9 for back. A tolerance of 1e-6
is 25 times that and still 100 times smaller than the smallest real mistake here (1e-4).
Relative to the largest value, because a projection has many bins near zero at the edge of the
field, where a relative error per bin is meaningless, and an absolute one depends on the units.

**The adjoint** (3). Matching the reference to 1e-6 in each direction bounds the error of each,
but OSEM's fixed point depends on the pair: a candidate whose back is computed with different
interpolation than its forward can stay within a loose tolerance of the reference in both
directions and still not be its own transpose. The dot-product test on the candidate alone is
cheap and catches that, and it is the test that would still work if there were no reference at
all.
