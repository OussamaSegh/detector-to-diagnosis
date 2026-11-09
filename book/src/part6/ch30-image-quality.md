# Image quality: resolution, contrast and noise {#ch30}

::: box-why
A reconstruction that passes its tests does what its model says. Whether the image is good enough
is a different question, and a specification, an acceptance test and a weekly quality check all
answer it with numbers: how sharp the image is, how much of a small object's contrast it keeps,
and how noisy its background is. Each of those numbers depends on choices that are easy to leave
out: the algorithm and its iterations, the post-filter, the pixel size, how a width is read off a
profile, and which pixels a region holds. On MiniDAQ, the same point source gives a width of 0.76
or 1.90 mm depending only on the pixel, and the same image a contrast of 0.99 or 1.29 depending
only on the region. This chapter measures MiniDAQ's images the way the standard for PET scanners
does, in 2D, fixes every choice in code and in tests, and turns the results into a protocol with
acceptance limits.
:::

**A day in the life.** After a software update of the reconstruction workstation, the weekly
phantom check at a PET site shows the smallest sphere's contrast down from 0.61 to 0.52. Every
other figure is inside its limits, the update's release notes say nothing about image quality,
and the vendor's service engineer finds the scanner in order. The cause is in the protocol, not
in the scanner: the update reset the post-filter of the site's brain protocol from 4 to 6 mm, the
default. Nobody would have seen a 15% loss of contrast in a small lesion by looking at images. The
check found it because the site had recorded, with its baseline, the protocol the baseline was
measured with, and compared each week's result with that baseline's limits. The fix was one line
in the protocol and a note in the change record; the lesson was that a figure of merit without
its protocol is not a specification.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Say what spatial resolution, contrast recovery and background variability measure, and which
   choices change each.
2. Measure a FWHM and a FWTM the way NEMA NU 2 describes, and choose the pixel size for it.
3. Explain why the resolution is measured by filtered backprojection, and what OSEM's width of a
   point says instead.
4. Compute a contrast recovery coefficient and a background variability from regions of interest,
   and place the regions by a rule.
5. Trade contrast against noise with the iterations and the post-filter, and choose a protocol
   from measurements.
6. Set acceptance limits from repeated measurements, and review a series of results for a trend.

## Prerequisites and estimated time {.unnumbered}

Chapter 27 (the corrections), Chapter 28 (the projector and OSEM) and Chapter 29 (the C++
projector, which makes the measurements fast; the numpy one gives the same numbers, slowly).
Reading: about 2.5 hours. Exercises: 2 hours. Milestone: 4 hours. If time is short, do Exercises
30.1 and 30.3.

## Three questions about an image

An image of a PET scanner is a map of activity concentration, and three properties decide what a
reader can see in it.

- **Spatial resolution.** How far apart two small objects must be to be seen as two, measured as
  the width of the image of a point: its full width at half maximum (FWHM) and at a tenth of the
  maximum (FWTM), which shows the tails.
- **Contrast recovery.** How much of a small hot object's true contrast over its background the
  image keeps. A small object's activity is spread over a larger area by the resolution (the
  partial volume effect), so its mean comes out lower than the truth, and an iterative
  reconstruction needs iterations to bring it back.
- **Noise.** How much the background varies where the activity is uniform. It hides small objects
  and sets how precisely a region's mean is known.

The three trade against each other. More iterations raise the contrast and the noise; a smoothing
filter lowers both; smaller pixels show finer detail with fewer counts each. A protocol is a choice
on those trades, and a specification states the protocol with its numbers.

The reference for how to measure them is NEMA NU 2, *Performance Measurements of Positron Emission
Tomographs*, the standard by which PET scanners are specified and compared, with the
corresponding IEC 61675-1 (verify: the editions your scanner's specification cites). It defines the
phantoms, the acquisitions, the reconstructions and the analysis for spatial resolution,
sensitivity, count rate performance and scatter fraction, the accuracy of the corrections, and
image quality. This chapter follows its methods for resolution and image quality, adapted to
MiniDAQ's 2D reconstruction, and describes them in its own words; the standard's text is what a
real test follows. What it leaves out of NEMA NU 2 is said at the end.

## Spatial resolution

### A width, measured the same way every time

A point's image is a few pixels wide, and reading a width off a few samples needs a rule. The
one NEMA NU 2 uses takes the maximum from a parabola through the highest sample and its two
neighbors, and finds each side's crossing of the level by linear interpolation between the two
samples around it (verify: the edition's wording):

```{.python include="tools/recon/quality.py" snippet="width"}
```

Both steps matter. Counting the samples above half the maximum, the obvious first version, gives a
whole number of samples: a Gaussian of 3.5 samples FWHM comes out 15% too narrow when it is centered
on a sample and 13% too wide when it is not, and the width jumps as the point moves. Interpolation
makes the width move smoothly with the profile. It still overestimates a curved side a little, up to
2.7% for the FWHM and 3.5% for the FWTM at 3.5 samples per FWHM and less than half of that at 7,
which is why the standard asks for pixels of at most a third of the expected FWHM (verify). The
parabola matters because both levels are fractions of the maximum: the highest sample of a peak
centered between two samples is 5.5% below the true maximum at that sampling, which widens the FWHM
by about 4%; the parabola's vertex is within 1.2%. Exercise 30.1 has you write both, against tests
with known answers.

Figure [](#fig-ch30-width) shows both steps on a sampled peak.

```{.figure #fig-ch30-width src="book/figures/plots/ch30/width.py" caption="Measuring a width the way NEMA NU 2 does, with the chapter's own functions, on a Gaussian of 3.5 samples FWHM centred between two samples. The parabola recovers the maximum the samples miss; the interpolated crossings give a FWHM of 3.60 samples for a true 3.5." alt="Samples of a Gaussian profile as stems, the true profile dotted, and a parabola through the three highest samples whose vertex at 0.988 is above the highest sample at 0.945. Horizontal lines mark the FWHM at half the maximum, 3.60 samples, and the FWTM at a tenth, 6.60 samples." width="75%" inputs="tools/recon/quality.py"}
```

`width` refuses a profile that does not fall below the level on both sides, which happens when
the profile is cut too short or a neighboring object is too close. A function that returned a
number there would return the profile's length.

A profile through a 2D image also needs a direction and a thickness. `point_profiles` takes the
row and the column through the brightest pixel, each summed over a band of pixels across it, so
that the profile does not depend on the one row that happens to hold the peak. For a point on the
x axis, the row is the radial direction (toward the axis) and the column the tangential one.

### FBP, because it has no iterations

NEMA NU 2 measures the resolution with filtered backprojection (FBP) and no smoothing (verify).
The reason is in the next section: OSEM's width of a point depends on the iterations, the subsets
and the counts, and the point would measure the reconstruction, not the scanner. FBP is a linear
operation with nothing to choose but its filter. It inverts the projection exactly for continuous,
complete data: filter each view along s with the ramp filter |f|, then backproject.

```{.python include="tools/recon/fbp.py" snippet="ramp"}
```

The filter is the ramp sampled in space, the discrete kernel of Kak and Slaney, rather than |f|
sampled in frequency, whose zero-frequency term is wrong for a finite kernel and leaves the image
with an offset. MiniDAQ's bins are not equally spaced in s, so `fbp` first interpolates each view
onto a grid of the central bins' spacing, pi R / N = 1.28 mm (the arc correction), and takes each
view at its mean angle, at most pi / 2N from each of its bins' own. It backprojects with the
projector of Chapter 28 or 29, whose `back` is a backprojection with linear interpolation. The test
`test_fbp_gives_a_disc_its_value_and_a_point_its_place` reconstructs a disc from its exact
projections and gets its value within 1% (it got 0.99996, with 0.6% rms inside), and a blob at
(40, -26) mm within 0.5 mm of where it is (SRS-IQ-002).

### MiniDAQ's resolution

The measurement is NEMA's in 2D: a point source in air, 1 MBq for 2 s, at 10, 50 and 100 mm from
the axis, each a run of the simulator with the scanner of Chapter 27, corrected for randoms and
normalization, all slices summed, and reconstructed by FBP at four pixel sizes
(`measurements/ch30/quality.txt`, section 1). At the pixel size the rule allows:

| Point at | Pixel | Radial FWHM | Radial FWTM | Tangential FWHM | Tangential FWTM |
|---:|---:|---:|---:|---:|---:|
| 10 mm | 0.25 mm | 0.76 mm | 2.83 mm | 1.65 mm | 2.76 mm |
| 50 mm | 0.5 mm | 2.97 mm | 5.21 mm | 1.84 mm | 3.21 mm |
| 100 mm | 0.5 mm | 5.05 mm | 8.25 mm | 2.31 mm | 5.00 mm |

: FBP of point sources in air (`measurements/ch30/quality.txt`, section 1).

Two things stand out. The tangential width grows slowly, from 1.65 to 2.31 mm. The radial width
grows fast, from under 1.4 mm to 5 mm at 100 mm: that is the parallax error. MiniDAQ's crystals are
15 mm deep, and a photon that arrives at an angle crosses into the next crystals before it
interacts, so the line is assigned to crystals further along than the ones it entered. The further
the point is from the axis, the more oblique its photons and the more the line's position spreads
radially. The point at 100 mm also comes out about 1 mm too far out (at 100.9 to 101.2 mm): the
lines are placed at 156 mm, the mean depth of interaction for photons that arrive square on
(Chapter 28), and oblique photons interact at a smaller radius on average. A scanner that measures
the depth of interaction reduces both; MiniDAQ does not.

What to expect at the center can be estimated from the parts (Moses, 2011): half the crystal
width, 2.45 mm / 2 = 1.23 mm, from where in its crystal the photon interacted, and the
non-collinearity of the two photons, about 0.0022 times the ring's diameter for the 0.5 degrees
FWHM the simulator draws, 0.69 mm at 312 mm, added in quadrature: about 1.4 mm. The simulator has
no positron range and no error in finding the crystal, which add to a real scanner's width.

Figure [](#fig-ch30-resolution) draws section 1 against the point's position and section 2 against the iterations.

```{.figure #fig-ch30-resolution src="book/figures/plots/ch30/resolution.py" caption="Point sources in air. Left, FBP: the radial width grows with the distance from the axis (parallax), the tangential one barely, and 2 mm pixels hide both. Right, OSEM: the widths settle within an iteration or two and differ from FBP's (hollow markers)." alt="Left: FWHM in mm against the point's distance from the axis, 10, 50 and 100 mm. With 0.25 mm pixels the radial width rises from 0.76 to 4.8 mm and the tangential from 1.65 to 2.3 mm; with 2 mm pixels both start near 3.7 mm. Right: OSEM widths against iterations 1 to 32 for points at 10, 50 and 100 mm, nearly flat at about 1.5, 1.7 and 2.6, and 2.0 and 5.3 mm, with FBP's values as hollow markers." width="100%" inputs="measurements/ch30/quality.txt"}
```

### The pixel and the bins

The same point at 10 mm, at four pixel sizes:

| Pixel | Radial FWHM | Tangential FWHM | Radial FWHM, 0.64 mm further out |
|---:|---:|---:|---:|
| 0.25 mm | 0.76 mm | 1.65 mm | 1.16 mm |
| 0.5 mm | 1.16 mm | 1.73 mm | 1.35 mm |
| 1 mm | 1.90 mm | 2.08 mm | 1.73 mm |
| 2 mm | 3.68 mm | 3.74 mm | 2.53 mm |

: FBP of the point at 10 mm and of one 0.64 mm further out, half a radial bin
(`measurements/ch30/quality.txt`, section 1).

At 2 mm the pixel is wider than the point's image, and the width measured is mostly the pixel's.
At 1 mm the rule of a third of the FWHM is not met either. The tangential width settles at 0.5 mm
and below. The radial width near the axis does not settle at all: it changes with the pixel and
with where the point falls among the radial bins, from 0.76 to 1.35 mm. The reason is MiniDAQ's
radial sampling. Its bins are 1.28 mm apart at the center, about the width of the response it is
trying to measure, so the data hold too few samples across a point to define its width, and the
unwindowed ramp filter of undersampled data rings. A real scanner's bins are half its crystal
pitch too, but its response is wider (positron range, crystal identification), so its center is
better sampled. For MiniDAQ, a central radial resolution is a range, with its conditions, not a
number. At 50 mm and beyond, where the response is wider, the FWHMs change by at most 0.33 mm
between 0.25 and 0.5 mm pixels.

### The same points by OSEM

Reconstructed by OSEM with 8 subsets, randoms and normalization in the model, at 0.5 mm, the same
points give (section 2):

| Point at | Width | Iteration 1 | Iteration 4 | Iteration 32 | FBP |
|---:|---|---:|---:|---:|---:|
| 10 mm | radial FWHM | 1.47 | 1.58 | 1.61 | 1.16 |
| 10 mm | tangential FWHM | 1.45 | 1.51 | 1.52 | 1.73 |
| 50 mm | radial FWHM | 2.65 | 2.59 | 2.55 | 2.97 |
| 100 mm | radial FWHM | 5.19 | 5.27 | 5.29 | 5.05 |
| 100 mm | tangential FWHM | 2.08 | 2.08 | 2.04 | 2.31 |

: OSEM's widths of the points in air, in mm, against FBP's at the same pixel
(`measurements/ch30/quality.txt`, section 2).

OSEM's widths are not FBP's: narrower tangentially everywhere and radially at 50 mm, wider radially
at 10 and 100 mm. A hot point in air is the easiest object an iterative reconstruction can get:
nothing around it, high counts, and the model's own sampling (Joseph's linear interpolation
between lines 1.28 mm apart) as the only limit. It converges in one or two iterations here and
then barely changes. Section 2b puts the points in the water, on the background's activity: the
widths are within 0.25 mm of those in air and converge as fast. Points are not where the iterations
show; small extended objects in a warm background are, as the next section measures.

So a resolution quoted from an iterative reconstruction says something about that reconstruction
with those settings, and can be made to look better than the scanner by choosing the object and
the iterations. NEMA's FBP number is comparable between scanners because there is almost
nothing to choose. A datasheet that quotes both should say which is which (assumption: confirm
with team which reconstruction your scanner's specification uses for resolution).

## Contrast and noise

### Regions of interest

NEMA NU 2's image quality test uses a body-shaped phantom with six spheres of 10 to 37 mm inner
diameter in a warm background, filled four times as hot as the background (eight in later
editions as an option), and measures in the reconstructed images (verify):

- each hot sphere's contrast: its region's mean over the background's, less one, over the true
  ratio less one, in percent;
- the background variability for each sphere size: twelve background regions of that size on the
  central slice and on slices 1 and 2 cm either side, sixty in all, and the standard deviation of
  their means over their mean.

MiniDAQ's version is 2D, with the phantom of Chapter 28: a water cylinder of 90 mm radius with
activity in 80 mm, and rods of 12, 8 and 5 mm radius at four times the background. The figures
of merit are three short functions:

```{.python include="tools/recon/quality.py" snippet="roi"}
```

The contrast recovery coefficient (CRC) is NEMA's percent contrast as a fraction: 1 when the image
has the true contrast, 0 when the rod is no hotter than the background. Both the measured and the
true ratios have 1 subtracted, because contrast is what is above the background; the ratio of
the ratios, the obvious first version, gives 0.25 for an image with no contrast at all.

The background variability is the spread of the regions' means, not of the pixels. A region's
mean averages its pixels' noise down, so the spread of regions of one size says how well an
object of that size is measured, and it is smaller for bigger regions: with independent pixel
noise of 10%, regions of 3 mm radius varied by 1.8% and regions of 6 mm by 0.92%, while the pooled
pixels said 10% for both (Exercise 30.2). That is why the variability is reported per size, next
to that size's contrast.

### Placing the background regions

Where the background regions go changes their means: too close to a rod and its spill-over raises
them, too close to the phantom's edge and the edge lowers them. `place_background_rois` places
them by a rule: on a 2 mm grid, inside 70 mm of the axis (10 mm from the activity's edge), the
12 mm regions 8 mm or more from every rod's edge, 22 mm apart, chosen from the axis outward with
ties broken by angle. The same arguments give the same twelve centers every time, and arguments
that do not fit twelve regions are refused (SRS-IQ-003). The smaller regions use the same centers,
as NEMA's concentric regions do. In MiniDAQ's phantom, with no slice free of rods, the twelve
12 mm regions overlap by up to 2 mm; a 3D phantom has room for more.

Figure [](#fig-ch30-rois) shows where the rule put them.

```{.figure #fig-ch30-rois src="book/figures/plots/ch30/rois.py" caption="The phantom's regions of interest: the three rods, and the twelve background regions at each of the three sizes, placed by rule inside 70 mm of the axis and away from the rods." alt="A water disc of 90 mm radius with activity to 80 mm and a dotted circle at 70 mm. Three filled rods of radius 12, 8 and 5 mm. Twelve sets of three concentric circles, radii 12, 8 and 5 mm, spread over the background away from the rods; some of the largest touch." width="50%" inputs="measurements/ch30/quality.txt measurements/ch28/reconstruct.py"}
```

### Iterations and filters

The phantom's first realization, reconstructed by OSEM with all the corrections in the model at
2 mm pixels, with and without a Gaussian post-filter (section 3):

| Image | CRC 12 mm | 8 mm | 5 mm | BV 12 mm | 8 mm | 5 mm |
|---|---:|---:|---:|---:|---:|---:|
| iteration 2 | 0.91 | 0.79 | 0.43 | 2.5% | 2.5% | 4.5% |
| iteration 4 | 1.04 | 1.01 | 0.68 | 2.3% | 3.3% | 7.9% |
| iteration 4, 4 mm filter | 0.99 | 0.92 | 0.58 | 2.1% | 2.8% | 6.2% |
| iteration 4, 6 mm filter | 0.95 | 0.85 | 0.50 | 2.0% | 2.6% | 4.9% |
| iteration 8 | 1.07 | 1.07 | 0.81 | 3.0% | 4.7% | 12.6% |
| iteration 16 | 1.08 | 1.09 | 0.87 | 3.8% | 6.1% | 16.9% |
| iteration 16, 4 mm filter | 1.01 | 0.96 | 0.70 | 2.8% | 4.5% | 12.2% |

: Contrast recovery (CRC) and background variability (BV) of the hot rods
(`measurements/ch30/quality.txt`, section 3).

Here are the iterations that the points did not show. The 5 mm rod's contrast doubles between
iterations 2 and 16, from 0.43 to 0.87, and its background variability almost quadruples, from
4.5% to 16.9%. The 12 mm rod is near its contrast by iteration 4 and slightly above 1 after that,
which Chapter 28 traced to the scatter estimate (about +0.08) and to one realization's spread
(about 0.1). A post-filter takes some of both back: at iteration 16 a 4 mm filter costs the 5 mm
rod 0.17 of contrast and saves 4.7 points of variability.

There is no best image in this table, only a choice. A protocol for small lesions might take more
iterations and accept the noise; one for quantifying a large region might filter more. MiniDAQ's
protocol is OSEM with 4 iterations of 8 subsets and a 4 mm Gaussian: the 12 mm rod's contrast at
about 1, the 8 mm rod's above 0.9, and variability of a few percent. A clinical protocol is chosen
by the people who read the images, from measurements like these and from patient images
(assumption: confirm with team who decides a reconstruction protocol and on what evidence).

Figure [](#fig-ch30-tradeoff) plots each rod's choices.

```{.figure #fig-ch30-tradeoff src="book/figures/plots/ch30/tradeoff.py" caption="Contrast against background variability for each rod, at 2, 4, 8 and 16 iterations, without a filter and with Gaussian filters of 4 and 6 mm. More iterations move an image up and to the right; a filter moves it down and to the left." alt="Three panels for the 12, 8 and 5 mm rods. Each shows contrast recovery against variability in percent for three series: no filter, 4 mm filter and 6 mm filter, each through iterations 2, 4, 8 and 16. The 5 mm rod's unfiltered series rises from 0.43 at 4.5% to 0.87 at 16.9%; the filtered series lie lower and further left." width="100%" inputs="measurements/ch30/quality.txt"}
```

## Is the number repeatable?

A figure of merit from one image is one draw from its distribution. Six independent realizations of
the phantom, each a new simulation of the background and the three rods with its own randoms and
scatter estimates, reconstructed with the protocol (section 4):

| Realization | CRC 12 mm | 8 mm | 5 mm | BV 12 mm | 8 mm | 5 mm |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0.995 | 0.923 | 0.581 | 2.1% | 2.8% | 6.2% |
| 2 | 0.951 | 0.809 | 0.605 | 3.3% | 5.0% | 6.3% |
| 3 | 1.018 | 0.906 | 0.642 | 4.1% | 6.1% | 8.7% |
| 4 | 0.951 | 0.885 | 0.586 | 3.9% | 4.2% | 4.5% |
| 5 | 0.961 | 0.856 | 0.617 | 2.2% | 3.5% | 5.4% |
| 6 | 0.979 | 0.886 | 0.583 | 3.7% | 4.2% | 6.5% |
| mean | 0.976 | 0.877 | 0.602 | 3.2% | 4.3% | 6.3% |
| SD | 0.027 | 0.040 | 0.024 | 0.9% | 1.1% | 1.4% |

: The protocol (OSEM 4 x 8, 4 mm Gaussian) on six realizations
(`measurements/ch30/quality.txt`, section 4).

The 8 mm rod's contrast ranges from 0.81 to 0.92 between realizations of the same phantom on the
same scanner with the same software: a change of 0.1 between two weekly checks means nothing by
itself. The background variability is itself a noisy number, from 2.1% to 4.1% for the 12 mm
regions. And six results say little about their own spread: from the chi-square distribution with
5 degrees of freedom, the true standard deviation is between 0.62 and 2.45 times the one estimated
from six, at 95% confidence. Limits set from six results are a start, to be narrowed as results
come in.

## The region decides the number

The protocol's image of the first realization, with the same background and five definitions of
the hot rod's region (section 5):

| Region | CRC 12 mm | 8 mm | 5 mm |
|---|---:|---:|---:|
| the rod (radius r) | 0.99 | 0.92 | 0.58 |
| its inner half (r / 2) | 1.21 | 1.21 | 0.78 |
| the rod, 2 mm off | 0.97 | 0.88 | 0.53 |
| the rod, 4 mm off | 0.90 | 0.76 | 0.40 |
| its hottest pixel | 1.29 | 1.34 | 0.83 |

: The same image's contrast recovery for five regions (`measurements/ch30/quality.txt`,
section 5).

The inner half avoids the blurred edge and reads 0.2 higher; Chapter 28 used it. A region 2 mm off,
a registration error of one pixel, costs the 5 mm rod 0.05; 4 mm off costs it a third of its
contrast. The hottest pixel, the analog of the maximum value that clinical quantification often
reports, reads highest of all, because it picks the noise's highest draw, and it is the least
repeatable: over the six realizations its SD was 0.032, 0.076 and 0.055 for the three rods,
against 0.027, 0.040 and 0.024 for the mean over the rod. None of these is wrong. Each is a
different figure of merit, and a specification that says "contrast recovery" without the region
says nothing that can be checked. MiniDAQ's region is the whole rod, placed at its known position.

Figure [](#fig-ch30-repeat) puts the realizations and the regions side by side.

```{.figure #fig-ch30-repeat src="book/figures/plots/ch30/repeat.py" caption="Two sources of variation in one figure of merit. Left, the protocol on six realizations of the same phantom, with their mean and SD. Right, one image measured with five definitions of the region: the choice moves the number more than the noise does." alt="Left: dots for six realizations of each rod's contrast recovery, around 0.98 for 12 mm, 0.88 for 8 mm and 0.60 for 5 mm, with error bars of 0.027, 0.040 and 0.024. Right: grouped bars for the three rods and five regions: the rod, its inner half, the rod 2 mm off, 4 mm off, and its hottest pixel; the inner half and the hottest pixel read highest, 4 mm off lowest." width="100%" inputs="measurements/ch30/quality.txt"}
```

## From figures to a specification

A specification for image quality is a protocol and a set of limits:

- the phantom and its preparation (activities, ratio, positions);
- the acquisition (duration, energy and coincidence windows);
- the reconstruction (algorithm, iterations, subsets, pixel, filter, corrections);
- the analysis (regions, their sizes and placement, the width method, the pixel for resolution);
- the figures of merit and their limits.

For MiniDAQ, SRS-IQ-004 states it: with the protocol, the 12 mm rod's CRC between 0.90 and 1.10,
the 8 mm rod's at least 0.75, and the background variability of the 12 mm regions at most 6%. The
six realizations meet it with room: the lowest CRCs were 0.951 and 0.809 and the highest
variability 4.1%. The limits are a design input, not a fit to these results; the realizations show
that a correct system passes them, by about three standard deviations. The method is M,
measurement, and the evidence is section 4 of the measurement, re-run after every change to the
reconstruction, its corrections or the protocol (assumption: confirm with team the acceptance values
of your scanner's image quality specification).

A weekly check uses the same protocol and compares each result with limits from the acceptance
baseline: the baseline's mean plus and minus three standard deviations, fixed when the scanner was
accepted. Two rules matter, and Exercise 30.3 has you write both.

- **The results under review never move the limits.** Limits computed from all the results there
  are widen with every week of a drift, and a slow drift stays inside them. In the exercise, a
  contrast that falls 0.45 SD a week leaves the baseline's limits in week 7; with the limits pooled,
  it was still inside in week 11, 5 SDs low.
- **A run finds what the limits let through.** A shift of one SD rarely leaves 3 SD limits (about
  one result in 44), but puts most results on one side of the mean. Seven in a row on one side is
  a finding: for a stable process, the expected wait for one is 2^7 - 1 = 127 results, about two
  and a half years of weekly checks. Run rules come from statistical process control (the Western
  Electric rules use eight in a row and Nelson's rules nine; verify); the length is part of the
  protocol.

The day in the life is this rule at work: the contrast fell outside the baseline's limits, the
protocol recorded with the baseline showed the filter had changed, and the record of the update
was corrected.

::: box-regulated
- **Image quality is a requirement with evidence.** SRS-IQ-004 is verified by measurement; its
  evidence names the measurement and its date, and is re-run when the reconstruction changes. The
  figures of merit it uses have requirements of their own (SRS-IQ-001 to SRS-IQ-003), verified by
  tests with known answers, because a wrong figure of merit would let a degraded image pass.
- **A control for H-13.** RC-44 measures the protocol with phantoms by tested methods and accepts
  it against limits; H-13's residual risk now names what it does not cover: 3D, real phantoms,
  the clinical protocols.
- **The tool.** `quality.py` and `fbp.py` are part of tool TL-31; its use and its evidence now
  include them (tool list).
- **The protocol is configuration.** The iterations, subsets, filter and pixel of a protocol are
  as much a part of the image as the code. A change to a default, as in the day in the life, is a
  change to be controlled and verified like a code change (assumption: confirm with team how
  reconstruction protocols are controlled at your organization and at the sites).
- **The standard's text.** A test report that claims NEMA NU 2 follows the edition's own text and
  states every deviation from it; this chapter's 2D adaptation is not a NEMA measurement.
:::

::: box-mistakes
- **A width counted in samples.** It jumps as the point moves. Interpolate, from a parabolic peak.
- **A resolution with a pixel wider than a third of it.** The pixel's width is measured. State the
  pixel with the result.
- **A resolution from OSEM, quoted as the scanner's.** It depends on the object, the iterations and
  the counts. Use FBP, or say what it is.
- **The background variability from the pixels.** It is the noise of a pixel, not of an object's
  mean. Use the regions' means, per size.
- **A contrast as the ratio of ratios.** It reads 0.25 with no contrast. Subtract one from both.
- **A region "around the rod".** The region changed the number by up to 0.4 here. Define it, size
  and position, in the protocol.
- **Limits from the results being judged.** A drift widens its own limits. Fix the baseline.
- **A figure of merit without its protocol.** Record the protocol with every result.
:::

::: box-askteam
1. Which edition of NEMA NU 2 (or IEC 61675-1) does our specification cite, and which deviations
   from it are recorded?
2. Which reconstruction and settings are used for the resolution figure in our datasheet? For the
   image quality figures?
3. Which protocol and limits does the acceptance test after installation use, and who set the
   limits, from how many results?
4. Is there a weekly or monthly phantom check at the sites? Which figures, which limits, which
   trend rules, and who reviews them?
5. How is a change to a reconstruction protocol's default controlled, and does it trigger a
   re-measurement?
6. Do our quantitative values (SUV, recovery coefficients) take a region's mean or its maximum, and
   is that stated where they are reported?
:::

## What this leaves out

MiniDAQ's measurements are 2D and simulated. NEMA NU 2 also measures, and a scanner's specification
also states: the axial resolution and the resolution off the axial center; sensitivity; count rate
performance, the noise-equivalent count rate and the scatter fraction (Chapter 11 measured all
three on MiniDAQ); the accuracy of the corrections for attenuation and scatter, with a lung
insert in the image quality phantom; and, for a time-of-flight scanner, the timing
resolution. A clinical evaluation adds task-based measures, observers detecting lesions in images,
which say more about diagnostic performance than any of these numbers (assumption: confirm with team
which of these your scanner's design verification includes).

## Exercises {.unnumbered}

**Exercise 30.1 (S): A width that does not depend on the pixels.** *Goal:* measure a FWHM and a
FWTM from a parabolic peak and linear interpolation. *Starter:*
`exercises/ch30/e1_width/starter/width.py`. *Acceptance:* `tests/test_width.py` passes: straight
sides measured exactly, a Gaussian of 3.5 samples FWHM within 4% wherever it falls and one of 7
within 1.5%, the peak between samples found, and a profile that does not fall refused. Then answer
in `NOTES.md` how far off the starter was, why the parabola matters, and which of section 1's
pixel sizes meet the rule of a third. *Time:* 30 minutes.

**Exercise 30.2 (S): Contrast and noise from regions of interest.** *Goal:* compute a contrast
recovery coefficient and a background variability from regions. *Starter:*
`exercises/ch30/e2_regions/starter/regions.py`. *Acceptance:* `tests/test_regions.py` passes: the
true contrast gives 1 and none gives 0, regions of known levels give their sample standard
deviation over their mean, and white noise averages down with the region's size. Then answer in
`NOTES.md` what the starter gave and why, and whether the 5 mm regions' higher variability means a
noisier image. *Time:* 30 minutes.

**Exercise 30.3 (M): Acceptance limits and a trend.** *Goal:* review weekly results against
limits from a fixed baseline, and find a small shift by its run. *Starter:*
`exercises/ch30/e3_qc/starter/qc.py`. *Acceptance:* `tests/test_qc.py` passes: limits of three
sample standard deviations, a baseline of fewer than five refused, a single result outside reported
where it is, a drift reported when it leaves the baseline's limits, and a shift of one SD reported
at its seventh result in a row. Then answer in `NOTES.md` why the starter missed the drift, how
often a stable process gives a false run, and what six results can say about their spread. *Time:*
45 minutes.

## MiniDAQ milestone: image quality {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ's reconstruction has a protocol with measured image quality: the resolution of
point sources by FBP, the contrast and background variability of the hot rods, their
repeatability, and acceptance limits, all by methods that tests fix. **Start:** tag `ch29`.
**End:** tag `ch30`.
:::

1. Write change request CR-0016 and ADR 0025; add SRS-IQ-001 to SRS-IQ-004 (SRS version 19) with
   SRS-IQ-004's evidence in section 3, RC-44 under H-13, and extend TL-31; update the architecture
   description (version 16).
2. Add `tools/recon/quality.py` and `tools/recon/fbp.py`, and the tests `ImageQuality` in
   `tools/test_recon.py`, which `tools/test_recon_cpp.py` also runs on the C++ projector.
3. Add `measurements/ch30/quality.py`: the point sources, the six realizations of the phantom, and
   the five sections of `quality.txt`.
4. Add Exercises 30.1 to 30.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets; the trace matrix shows
SRS-IQ-001 to SRS-IQ-003 tested and SRS-IQ-004 measured; the protocol meets SRS-IQ-004 on every
realization; every starter of the chapter fails. Tag `ch30`.

## Check yourself {.unnumbered}

1. What do the FWHM and the FWTM each tell you about a point's image?
2. Why does NEMA NU 2 measure the resolution with FBP?
3. Why does counting samples above half the maximum give a width that jumps?
4. What does the parabola through three samples correct?
5. What sets the pixel size for a resolution measurement, and what happened at 2 mm?
6. Why does MiniDAQ's radial width grow from the center to 100 mm, and why does the point at
   100 mm come out 1 mm too far out?
7. Why is MiniDAQ's central radial resolution a range and not a number?
8. Why did OSEM's width of a point converge in one or two iterations, and what does that say about
   resolution figures from iterative reconstructions?
9. Write the contrast recovery coefficient. What does the ratio of ratios give for no contrast?
10. Why is the background variability the spread of regions' means and not of pixels, and why is
    it reported per size?
11. What did more iterations do to the 5 mm rod's contrast and variability, and what did a 4 mm
    filter do?
12. How far apart were the 8 mm rod's contrasts between realizations, and what does that mean for
    a weekly check?
13. How much did the region's definition change the 12 mm rod's contrast?
14. Why must the results under review not move the limits?
15. What does a run rule find that the limits do not, and how often does a stable process trigger
    a run of seven?

## Summary {.unnumbered}

- Resolution, contrast recovery and noise trade against each other through the iterations, the
  filter and the pixel; a figure of merit without its protocol is not a specification.
- A width is read from a parabolic peak and linear interpolation, with pixels of at most a third
  of it, and refused when the profile does not fall on both sides.
- The resolution is measured by FBP with an unwindowed ramp, which has nothing to choose. MiniDAQ's
  tangential FWHM is 1.65 to 2.31 mm from 10 to 100 mm; the radial one grows to 5 mm at 100 mm
  from parallax; near the center it depends on the pixel and the point's position (0.76 to
  1.35 mm), because the bins are as wide as the response.
- OSEM's width of a point converges in one or two iterations and differs from FBP's; it describes
  the reconstruction, not the scanner.
- Contrast recovery is (hot / background - 1) / (true ratio - 1); background variability is the
  spread of twelve regions' means of each size, placed by a rule.
- From iteration 2 to 16, the 5 mm rod's contrast went from 0.43 to 0.87 and its variability from
  4.5% to 16.9%. The protocol, OSEM 4 x 8 with a 4 mm filter, gave the 12 mm rod 0.976 (SD 0.027)
  over six realizations.
- The region changes the number by up to 0.4, and the hottest pixel is the least repeatable choice.
- SRS-IQ-004 sets the limits, verified by measurement; a weekly check compares with limits from a
  fixed baseline and looks for runs.

## Further reading {.unnumbered}

- NEMA NU 2, *Performance Measurements of Positron Emission Tomographs*, National Electrical
  Manufacturers Association (verify: the current edition, 2018 or later).
- IEC 61675-1, *Radionuclide imaging devices: Characteristics and test conditions, Part 1:
  Positron emission tomographs* (verify: the current edition).
- A. C. Kak and M. Slaney, *Principles of Computerized Tomographic Imaging*, IEEE Press, 1988,
  reprinted by SIAM, 2001: chapter 3 for filtered backprojection and the discrete ramp filter.
- W. W. Moses, "Fundamental limits of spatial resolution in PET", *Nuclear Instruments and Methods
  in Physics Research A* 648 (2011) S236 to S240 (verify).
- E. J. Hoffman, S.-C. Huang and M. E. Phelps, "Quantitation in positron emission computed
  tomography: 1. Effect of object size", *Journal of Computer Assisted Tomography* 3 (1979) 299 to
  308, for the partial volume effect (verify).
- S. R. Cherry, J. A. Sorenson and M. E. Phelps, *Physics in Nuclear Medicine*, 4th edition,
  Elsevier Saunders, 2012: the chapters on PET performance and image quality.
- L. S. Nelson, "The Shewhart control chart: tests for special causes", *Journal of Quality
  Technology* 16 (1984) 237 to 239, and the Western Electric *Statistical Quality Control
  Handbook* (1956), for run rules (verify).
- ADR 0025 and CR-0016 in the repository: the decision and the change record.
