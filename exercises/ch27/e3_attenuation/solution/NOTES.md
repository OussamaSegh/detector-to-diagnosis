# Exercise 27.3: notes on the solution

**The three mistakes.**

- *A circle is not a head.* For a head 160 by 200 mm turned 20 degrees and 11 mm off center, the
  circle of the mean radius (90 mm) gets lines wrong by up to 20 mm of water at the long and short
  axes and more at the edges: its correction factors ranged from 0.51 to 1.85 times the
  ellipse's over the lines that cross at least 20 mm of the head. The ellipse's chord is exact
  for the ellipse; a real head is neither, which is why the outline comes from the emission data
  or an MR image, and why its error is a risk (H-12).
- *Units.* `exp(mu L)` with mu in 1/cm and L in mm is `exp(10 mu L)`: for 200 mm of water the
  starter gave `exp(19.2)`, about 2 x 10^8, instead of 6.8. The test of one known value catches it;
  the type system would catch it if the lengths carried their unit, as the C++ side does with
  `std::chrono` for times.
- *The decay during the frame.* Counting from the frame's start forgets that the activity keeps
  falling while the frame runs. The factor for the frame is the start's `exp(lambda t0)` times
  `lambda T / (1 - exp(-lambda T))`, the ratio of the activity at the start to the mean over the
  frame.

**The head** (Then, by hand, 1). Through 180 mm of water the factor is `exp(0.096 x 18)` = 5.63.
An outline 5 mm too large all round adds 10 mm to that line: `exp(0.096)` = 1.10, so the line
comes out 10% high, and lines near the edge, where the chord changes fastest, more.

**The frame** (2). From 60 to 70 minutes the factor is 1.5072. The starter's, at the start only,
is 1.4606, 3.1% low; at the middle of the frame, 1.5075, 0.02% high. The middle of the frame is
good enough when the frame is short against the half-life; for frames of tens of minutes of a
short-lived tracer (oxygen-15, 2 min; verify: half-lives from NIST), only the integral is.

**The line** (3). The two photons of a pair leave in opposite directions along the line, and both
must reach their crystals: the probability is `exp(-mu a) exp(-mu b)` for the lengths a and b on
either side of the annihilation, `exp(-mu (a + b))`, and `a + b` is the whole chord wherever the
annihilation was. In single-photon imaging only one photon travels, the attenuation depends on the
depth, and there is no correction this simple.
