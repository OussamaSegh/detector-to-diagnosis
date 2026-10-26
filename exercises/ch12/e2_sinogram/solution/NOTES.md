# Exercise 12.2: notes on the solution

**The three mistakes.**

- *Angles past 180 degrees.* For i + j + 1 >= 384 the starter wrapped the view with
  `% 192` but kept the distance: half the lines of response landed on the mirror image
  of their bin, so two lines shared a bin and others had none. The same line seen from
  the other side has angle - 180 degrees and the opposite signed distance: k - 384 and
  384 - d.
- *Delayed coincidences counted as prompts.* They estimate the randoms (Chapter 10) and
  belong in a sinogram of their own, which a reconstruction subtracts or models. Here
  12 of 6,167 coincidences, and far more at the activities of Chapter 11.
- *Arc-corrected positions.* r * pi * R / N is the spacing near the center, where
  sin x is x. At r = 113 the line is at 119.7 mm, not 138.7 mm. Real systems either
  keep the uneven spacing and tell the reconstruction (as MiniDAQ's header does) or
  resample to even spacing ("arc correction").

**The sinusoid** (Then, by hand, 1). For a point at (x0, y0), s(theta) = x0 cos theta +
y0 sin theta: the amplitude is the source's distance from the axis (47.2 mm), the phase
its angle (-32 degrees). Every point in the object draws one sinusoid; a sinogram is
their sum, which is where its name comes from.

**A scale, not a shift** (Then, by hand, 2). Measured (0.3 s at 2 MBq each):

| true x (mm) | 0 | 20 | 47 | 80 | 100 |
|---|---:|---:|---:|---:|---:|
| fitted x (mm) | 0.02 | 19.28 | 45.28 | 77.15 | 96.55 |
| ratio | | 0.964 | 0.963 | 0.964 | 0.966 |

The ratio is the same at every radius: the image is scaled. The simulator assigns a
single to the crystal that contains the interaction point, which is on average about
6 mm into the 15 mm crystal (for LYSO's 0.087 per mm, the mean depth of photons that
interact within 15 mm is 1/mu - 15 e^(-15 mu) / (1 - e^(-15 mu)) = 5.9 mm). The angles
of those points are right, but the binning places them on the front face, at 150 mm
instead of about 156 mm, which scales every distance by 150 / 156 = 0.962. Binning with
an effective radius of about 156 mm removes the scale; real scanners calibrate it.
Off-axis, the depth also blurs the lines radially (parallax), which a scale does not
remove: that is why brain scanners care about depth-of-interaction measurement
(assumption: confirm with team whether your scanner's detector measures it).
