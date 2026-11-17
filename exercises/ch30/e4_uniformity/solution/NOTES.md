# Exercise 30.4: notes on the solution

**The edge** (Then, by hand, 1). The starter reported about 96% for a perfectly uniform cylinder.
It took every pixel above zero, and the edge of the cylinder, blurred over 4 pixels as the
resolution blurs a real one, holds values from 1 down to almost 0. Uniformity is a property of
the inside of the field; the edge measures the resolution. The solution measures the central
field, 75% of the radius, and only pixels whose neighbors are all inside it, so the smoothing
does not pull the edge in.

**The noise** (2). With 2% noise per pixel the integral uniformity over the 4,112 usable pixels
is 6.6% without smoothing and 2.8% with it, and the smoothed image's noise is 0.77%. For
independent pixels the kernel divides the noise by the root of the sum of its squared weights,
sqrt(36 / 256) = 0.375. The extremes of four thousand pixels sit about 3.5 standard deviations
out, so the integral uniformity of pure noise is about 3.5 times the noise: a number that grows
with the field's size and the counts, and has to be compared with a limit set for the same
protocol.

**What each number sees** (3). A defective block, or one with a wrong gain, makes a local hole
or band: a step over a few pixels, which the differential uniformity sees, as it saw the cold
row along the columns. A wrong normalization or attenuation correction makes a slow gradient or
a bowl across the field: the integral uniformity sees it (3.6% for 5% at the edge) while the
differential stays near zero. Both are needed, and neither replaces looking at the image.
