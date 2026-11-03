# Exercise 30.2: notes on the solution

**The pixels and the regions** (Then, by hand, 1). The starter returned 10.0% for both sizes: the
standard deviation of the pooled pixels is the pixel noise, which the region's size does not
change. The solution's variability was 1.80% for regions of 3 mm (32 pixels) and 0.92% for 6 mm
(112 pixels), close to 10% over the square root of the pixels (1.77% and 0.94%). The question a
region answers is how well the mean of an object of that size is known, and that is what the
spread of the regions' means measures. The pooled pixels also mix in any difference between the
regions' levels with the noise inside them.

**The contrast** (2). The true ratio over the measured one reads 1 at the true contrast, but 0.25
when the hot region is no hotter than the background, and 0.625 for half the true contrast. It is
a ratio of concentrations, not a recovery of contrast: the contrast is what is above the
background, so both the measurement and the truth subtract 1 before dividing.

**Small regions** (3). Not the rod's image: the background regions of each size are drawn from
the same image and the same pixels. A region of 5 mm radius averages about 20 pixels of 2 mm, one
of 12 mm about 113, so its mean is about 2.4 times as noisy for independent pixels, and more than
that once the pixels are correlated, as an iterative image's are over a few millimeters. This is
why NEMA reports the variability per sphere size, beside that sphere's contrast.
