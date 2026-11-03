# Exercise 30.1: notes on the solution

**Counting samples** (Then, by hand, 1). The starter's width is a whole number of samples. For
the Gaussian of 3.5 samples FWHM it gave 3 samples when the center was on a sample (15% short)
and 4 when it was anywhere else (13% long): the count changes when a sample crosses the level,
not when the width does. Interpolating each side gives a width that moves smoothly with the
profile. Linear interpolation across a curved side still overestimates a little: up to 2.7% for
the FWHM and 3.5% for the FWTM at 3.5 samples per FWHM, and 0.4% and 1.1% at 7.

**The parabola** (2). Both levels are fractions of the maximum, so an error in the maximum moves
both. The highest sample of a Gaussian centered between two samples is 1.2% below its true peak
at 3.5 samples per FWHM. On the steep part of the profile, near half the maximum, a 1.2% lower
level moves each crossing only a little; near a tenth, where the sides are flatter in relative
terms, the same change of level moves the crossings further. The parabola puts the maximum within
0.2% here.

**The pixel** (3). The point at 10 mm has an FBP radial FWHM of 0.76 to 1.90 mm depending on the
pixel. A pixel of at most a third of the FWHM means 0.25 mm at most for a width near 0.8 mm, and
0.5 mm meets the rule only for the wider tangential width (1.73 mm) and for the points further
out. At 2 mm the pixel is wider than the point's image and the width measured is mostly the
pixel's: 3.68 mm. A width is meaningless without its pixel size, and a width near the sampling of
the data (1.28 mm between radial bins here) also depends on where the point falls among the bins.
