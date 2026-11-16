# Exercise 39.2: notes

The starter fails five of the six tests: with c instead of c / 2 its millimeters are twice too
long, and its density at each bin's center times the width does not add up to 1 when the bins
are wide (it gives the middle bin of the wide-bin test a "probability" of 2.8). The symmetry
test passes, since both mistakes are symmetric.

Design choices:

- A time difference tau places the point at c tau / 2, so every conversion from picoseconds to
  millimeters along a line carries the factor 1/2: the resolution, the bins' width, the edges.
- Integrate, do not sample. The two differ little when the bins are much narrower than the
  kernel (20 ps bins with a 300 ps resolution); with bins of the kernel's width, sampling is off
  by a few percent per bin, and with wider bins it is simply wrong.
- One erf per edge: K + 1 calls for K bins, half of what K pairs would cost, and the sum
  telescopes to the difference of the outer two, so it is 1 to rounding for a point inside.
  MiniDAQ's C++ projector does the same and skips the bins beyond 6 standard deviations.
