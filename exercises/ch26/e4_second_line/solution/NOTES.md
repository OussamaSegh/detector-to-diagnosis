# Exercise 26.4: notes on the solution

**The mistake.** The starter checked the curve on the photopeaks, the points the gains were made
from. With any E_sat, the gain is the one that puts the photopeak at 511 keV, so the check could
not fail: a test of a model on the data it was fitted to. The solution checks the 307 keV line,
which the calibration did not use, and the curve's error there is what a wrong E_sat changes.

**How far the line moves** (Then, by hand, 1). With the true E_sat of 1,500 keV, an E_sat of
1,800 keV puts the line at 310.5 keV (+1.1%) and one of 1,200 keV at 301.7 keV (-1.7%). A
linear detector (no saturation) puts it at 327.6 keV (+6.7%). An error of 10% in E_sat moves the
line by 0.6 to 0.8%, so the tolerance of 0.8% catches errors of more than about 13% (1,300 and
1,700 keV are refused, 1,350 and 1,650 keV pass). A peak's
center known to 0.2% puts the line's energy within about 0.3%: the tolerance has room for it, and
an error smaller than the tolerance stays invisible. A second line with a larger lever arm does
better.

**The median** (2). One crystal's ratio of codes is known to about 0.3% (two centers of 0.2%
each), and the ratio changes by only about 1% between E_sat of 1,500 and 1,800 keV, so one
crystal's estimate is off by up to about a hundred keV: in the test, from 1,430 to 1,590 keV for
the middle 80%. Forty independent estimates scatter around the truth, and their median came out
at 1,524 keV, 1.6% high. None was infinite here; with noisier peaks, a crystal whose noise pushes
the ratio above 511 / 307, the limit of a linear detector, gives infinity, and the median, unlike
the mean, does not care.

**Another line** (3). The farther the second line is from 511 keV, and the more saturated, the
more it sees: a line well below 511 keV, where the curve bends least like the photopeak's, or a
line far above it. 662 keV is close to 511 keV and the curve between them is nearly straight: an
E_sat 20% too high moves it by only 0.9%, against 1.1% at 307 keV. A source line must also be
inside the range the quadratic was fitted over (200 to 700 keV), or the check tests the
quadratic's range instead of E_sat.
