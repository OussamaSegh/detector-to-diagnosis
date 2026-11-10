# Image reconstruction: from sinogram to image with OSEM {#ch28}

::: box-why
A sinogram is not a picture of the patient. Each of its bins counts the coincidences along one
line, and the image is whatever distribution of activity explains those counts best. Finding it
is the reconstruction, and in almost every PET scanner today it is iterative: the algorithm
guesses an image, computes the counts it would have produced, compares them with the measured
ones and corrects the guess, again and again. You will not write the reconstruction of a
product as the DAQ lead. You will review it, feed it, test it and put it in the same regulated
release as your C++. This chapter builds a small one in Python, in 2D, on MiniDAQ's simulated
data, with the corrections of Chapter 27 inside its model. You will see an image that came out
3.6% too small because the lines were drawn at the wrong radius, a backprojector that looked fine
and was not the transpose of its projector, and the reason the noise of an image grows with
every iteration while its contrast stops improving after three.
:::

**A day in the life.** A physicist compares the new reconstruction with a CT of the same phantom
and finds that the hot rods near the edge of the field of view sit about 3 mm closer to the
center than they should, while the rods near the center are where they belong. The images are
sharp and the contrast is right, so nobody had noticed. The cause is one number: the
reconstruction places each line of response between the front faces of its two crystals, but
the photons are absorbed on average some millimeters inside the crystals, so the real lines are
longer and their distance from the axis is larger. A point source placed off center gives the
effective radius in an afternoon. The fix is a parameter, recorded with the scanner's
calibration, and a test that fails if a point source comes out in the wrong place.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Write the statistical model of PET data, counts Poisson with mean `m A x + b`, and say what
   each term holds.
2. Compute the line of every sinogram bin, and measure where the lines really are with a point
   source.
3. Implement a ray-driven projector and its exact adjoint, and prove the adjoint with the
   dot-product test.
4. Derive the MLEM update, explain why it keeps the image non-negative and the likelihood rising,
   and put the corrections into its model instead of the data.
5. Speed MLEM up with ordered subsets, choose the subsets, and compute each subset's
   sensitivity.
6. Measure contrast recovery and noise iteration by iteration, and explain why one image is not
   enough to judge a reconstruction.
7. Place a reconstruction tool, its settings and its hazards in a regulated life cycle.

## Prerequisites and estimated time {.unnumbered}

Chapter 8 (PET physics: lines of response, attenuation), Chapter 12 (the sinogram and its
binning), Chapter 27 (the corrections and `tools/recon`). You need Python 3 with numpy, and the
algebra of a matrix and its transpose. Reading: about 3 hours. Exercises: 3 hours. Milestone: 5
hours. If time is short, do Exercises 28.1 and 28.2.

## The problem

### A model of the data

Number the bins of a sinogram i and the pixels of the image j. A decay in pixel j is detected in
bin i with probability `a_ij`: the matrix A, the system matrix, holds the geometry of the
scanner. With the activity `x_j` in each pixel, the mean number of true coincidences of a perfect
scanner in bin i is `(A x)_i`. The real scanner multiplies that by the bin's normalization, its
attenuation and its live fraction, and adds randoms and scatter (Chapter 27). Collect the
factors into `m_i` and the additions into `b_i`:

$$\bar y_i = m_i \, (A x)_i + b_i$$

The counts `y_i` that the scanner records are Poisson with mean `ybar_i`, independent from bin
to bin. Reconstruction is the inverse problem: given y, m, b and A, find x.

Two features of this model decide everything that follows. The counts are Poisson, so a bin with
many counts is more certain than one with few, and a good estimate weights them accordingly. And
the corrections are part of the mean, not of the data: `y` is what was measured, and it stays
that way.

### Analytic or iterative

Filtered backprojection inverts the line integrals of an ideal, noiseless sinogram exactly: filter
each projection with a ramp, smear it back across the image, add the views. It is linear and
fast, and its noise and resolution are well understood. It needs data already corrected, and it
treats every bin as equally certain, so its images of low-count data have streaks, and the
pre-corrected data it needs has negative bins where the randoms were subtracted.

The iterative methods start from the model instead. Maximum-likelihood expectation maximization,
MLEM (Shepp and Vardi, 1982; Lange and Carson, 1984), finds the image whose expected counts make
the measured ones most probable. Its ordered-subsets version, OSEM (Hudson and Larkin, 1994),
made it fast enough for clinical use, and it or a variant of it is the reconstruction of most
clinical PET scanners since. This chapter builds OSEM with the corrections in the model (ADR 0023).

## The lines of a sinogram

### Each bin's own line

The projector needs each bin's line: its normal angle `phi` and its signed distance `s` from the
axis, so that the line is the set of points with `x cos(phi) + y sin(phi) = s`. For MiniDAQ's ring
of N = 384 crystals at angles `(i + 1/2) 2 pi / N`, the pair of crystals (i, j) with `k = i + j +
1` and `d = j - i` has its normal at `k pi / N` and lies at `s = R cos(d pi / N)`. Chapter 12's
binning puts the pair in view v and radial bin `r = d - N / 2`, so `s = -R sin(pi r / N)`.

One detail is easy to miss. Within a view, k is `2v` for odd r and `2v + 1` for even r: each view
of 192 interleaves two angles half a view apart. The sinogram header's angle is their mean. A
projector that used it for every bin would draw each line up to `pi / (2N)`, 0.23 degrees, off,
which is 0.4 mm at 100 mm from the axis. `bin_lines` gives every bin its own angle:

```{.python include="tools/recon/project.py" snippet="lines"}
```

### Where the photons interact

R is the radius at which the lines meet the crystals. The obvious value is the front face, 150
mm. But a 511 keV photon travels some millimeters into the crystal before it interacts, so the
event is recorded deeper, and the real line runs between two points below the faces. To find
where, `measurements/ch28/reconstruct.py` simulates a point source at (40, -25) mm in air and
reconstructs it with the lines at two radii:

| Lines at radius | x found | y found | Distance from the axis, found / true |
|---|---:|---:|---:|
| 150 mm | 38.58 | -24.11 | 0.9645 |
| 156 mm | 40.11 | -25.06 | 1.0028 |

: A point source at (40, -25) mm, OSEM with 8 subsets, 10 iterations, 1 mm pixels
(`measurements/ch28/reconstruct.txt`, section 1).

With the lines at the front faces the point comes out 3.6% too close to the axis. At 156 mm it
is within 0.3%. Everything that follows uses 156 mm. A real scanner's effective radius depends
on its crystals and the photons' angle of incidence, and is measured the same way, with a point
source or a set of them (assumption: confirm with team how your scanner's geometry is
calibrated, and whether the reconstruction models the depth of interaction).

## A projector and its adjoint

### Joseph's method

The system matrix of a 2D sinogram of 192 views and 227 bins and an image of 128 x 128 pixels has
43,584 rows and 16,384 columns, and almost all of its entries are 0: a line crosses a few hundred
of the pixels. A projector computes `A x` from the geometry without storing A as a matrix.
Siddon's method (1985) computes the exact length of the line in every pixel it crosses. Joseph's
method (1982), used here, steps through the image one column at a time (or one row, for a line
closer to the x axis), takes the image interpolated linearly between the two nearest pixels at
each step, and weights it by the length of the step:

```{.python include="tools/recon/project.py" snippet="joseph"}
```

The weights depend only on the geometry, so the class computes them once per view and keeps
them: 89 MB for MiniDAQ's 2D sinogram and a 128 x 128 image, built in 0.3 s. A forward
projection then takes 54 ms and a backprojection 44 ms on the reference machine. That is fine in
2D and much too slow in 3D, where the oblique planes multiply the lines by the number of ring
differences; Chapter 29 moves the projector to C++. Figure [](#fig-ch28-joseph) shows the steps on a small grid.

```{.figure #fig-ch28-joseph src="book/figures/tikz/ch28/joseph.tex" caption="Joseph's method on a small grid. The line takes one step per column; at each step it reads the image between the two nearest pixel centres of that column and weights it by the step's length." alt="A grid of 7 by 5 pixels with their centres as dots. A rising line crosses it; in each column a dot marks where the line passes, joined by a dotted segment to the two nearest pixel centres above and below. Notes say each step takes the interpolated image times the step length, and that back() uses the same weights in reverse." width="75%"}
```

### The adjoint and the dot-product test

MLEM needs the projector A and its transpose `A^T`, the backprojection: the second spreads each
bin's value back over the pixels on its line, with the weights the first used to gather them.
The two must be exactly a matrix and its transpose. A backprojection that is close but not exact
changes the algorithm's fixed point, so the image it converges to is not the maximum-likelihood
image of the data, and nothing in the image says so.

There is a test that proves it without forming the matrix. For any image x and any sinogram y,

$$\langle A x, y \rangle = \langle x, A^T y \rangle$$

and with random x and y the two sides agree to rounding only if the backprojection is the
adjoint. `Projection.test_the_backprojector_is_the_adjoint` runs it on every build. Exercise 28.1
asks you to write the backprojection of a simple projector that splats each pixel onto its two
nearest bins; the adjoint gathers from the same two bins with the same weights:

```{.python include="exercises/ch28/e1_adjoint/solution/adjoint.py" snippet="back"}
```

A backprojection that takes the nearest bin instead looks just as reasonable, and fails the test
by 0.25%. On a disc in the middle of the image it converges to the right answer anyway, which is
why the test exists.

Two more tests pin the geometry down. A disc projects to its chords, and an off-center object
lies on its sinusoid, `s = x0 cos(phi) + y0 sin(phi)`, in every view: a projector with its
angles shifted by half a view, or its sign of s reversed, fails the second.

## MLEM

### The update

The log-likelihood of the counts, without the terms that do not depend on x, is

$$L(x) = \sum_i \big( y_i \log \bar y_i - \bar y_i \big), \qquad \bar y_i = m_i (A x)_i + b_i$$

MLEM maximizes it with a multiplicative update. Each iteration computes the expected counts of
the current image, the ratio of measured to expected in every bin, backprojects the ratio
weighted by `m`, and divides by the sensitivity, the backprojection of `m` itself:

$$x_j \leftarrow \frac{x_j}{s_j} \sum_i m_i \, a_{ij} \, \frac{y_i}{\bar y_i}, \qquad s_j = \sum_i m_i \, a_{ij}$$

Where the image's expected counts are too low, the ratio is above 1 and the pixels on those
lines grow; where they are too high, they shrink. At the maximum the backprojected ratio equals
the sensitivity and the image stops changing. The update has properties you can test. A
non-negative image stays non-negative, because every factor is. The likelihood never decreases
from one iteration to the next, with or without `b` (Lange and Carson derive it). And without
the additive term, the total of the expected counts equals the measured total after every
iteration, so MLEM neither loses nor invents counts overall.

The sensitivity is not a constant. A pixel near the edge of the field of view lies on fewer
lines than one at the center, and a pixel whose lines cross the gaps between blocks contributes
to fewer measured bins. In Exercise 28.1 a pixel in the corner keeps 27.8 of its 36 views'
weight; a reconstruction that divides it by 36 takes it to 0.77 of its value in one iteration
started from the truth, and to 0.15 after 30.

### The corrections in the model

`tools/recon/mlem.py` implements the update for MLEM and OSEM together (OSEM in the next
section; with one subset it is MLEM):

```{.python include="tools/recon/mlem.py" snippet="osem"}
```

Three places carry the corrections: the expected counts `m A x + b`, the backprojected ratio
weighted by `m`, and the sensitivity, the backprojection of `m`. The counts `y` are never
divided, subtracted or clipped. A bin with `m = 0`, a line that was not measured because it falls
in a gap or belongs to a dead crystal, takes no part: its ratio is weighted by 0 and it adds
nothing to the sensitivity. `Reconstruction.test_unmeasured_bins_take_no_part` puts 1,000 counts
in every such bin and checks that the image does not change.

Figure [](#fig-ch28-loop) shows where each correction enters.

```{.figure #fig-ch28-loop src="book/figures/tikz/ch28/loop.tex" caption="One MLEM update. The measured counts are never changed: the corrections live in the expected counts, in the weighting of the ratio, and in the sensitivity." alt="A loop: image x, forward to the expected counts m A x plus b, the ratio of measured y to expected, backprojected with the weights m, divided by the sensitivity A transpose m, which multiplies x. A note says m holds normalization, attenuation and live fraction, b holds randoms and scatter, and a bin with m equal to 0 takes no part." width="90%"}
```

### What pre-correction costs

The alternative is to correct the data first, `(y - b) / m`, and reconstruct the result with a
plain MLEM. Exercise 28.2 does both on the same data and finds two failures.

The first is at low counts. With at most 1.3 true counts and 2 randoms per bin, `y - b` is
negative in many bins. Clipping them to 0, which MLEM needs, raises the mean of the corrected
sinogram: its sum came out 1.70 times the unclipped one. Over 20 noise realizations the
pre-corrected reconstruction put the excess into the background outside the object, 2.3 times
the background of the model-based one, and the object came out 7% low. More iterations did not
help. The model-based reconstruction's mean over the object was within 0.7% of the truth.

The second is the gaps. A pre-correction can only set a bin with `m = 0` to 0, and to MLEM a 0
is a measurement: no decay happened along that line. With every sixth radial bin unmeasured, the
pre-corrected disc came out in stripes, with a standard deviation of 1.08 against 0.023 with the
corrections in the model, and its likelihood went down in some iterations.

## OSEM

### Subsets of the views

Each MLEM iteration projects and backprojects every view once. OSEM divides the views into k
subsets and updates the image after each subset, with the same formula restricted to the
subset's views. One iteration still costs one projection and one backprojection of all views,
and makes k updates instead of one. While each subset is a fair sample of the whole data, k
updates on subsets do about as much as k MLEM iterations:

| Updates | MLEM | OSEM | MLEM gain | OSEM gain | MLEM CRC | OSEM CRC |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 8 | 1 | -36 | 0 | 0.77 | 0.78 |
| 16 | 16 | 2 | 3,111 | 3,117 | 1.13 | 1.14 |
| 1 | 1 | | -295,185 | | 0.10 | |

: MLEM and OSEM with 8 subsets on the phantom of the next section; the log-likelihood relative
to OSEM's first iteration, and the CRC of the 12 mm rod. The MLEM and OSEM columns are numbers of
iterations (section 3 of the measurement).

One OSEM iteration of 8 subsets reaches the likelihood and the contrast of 8 MLEM iterations, at
the cost of one. The last row is what that cost buys in MLEM: one iteration, far behind.

What makes a subset fair is that its views spread over the whole half turn. MiniDAQ's 8 subsets
of 192 views each hold every eighth view, 7.5 degrees apart (`mlem.subsets`). Each subset also
needs its own sensitivity, the backprojection of `m` over its own views: the full sensitivity
divided by k is right only when every subset has as many views and the same factors, and
attenuation and the gaps make `m` differ from view to view. Exercise 28.3 measures both mistakes
on 36 views in 5 subsets, which do not divide evenly. With interleaved subsets and their own
sensitivities, 4 iterations came within 0.39% rms of 20 MLEM iterations. Contiguous blocks of
views, or the shortcut of the full sensitivity over 5, each put it more than 3% away, and both
together 21%.

OSEM gives up two properties of MLEM. Its likelihood can fall from one iteration to the next,
and with noisy data it does not in general converge to the maximum-likelihood image but
approaches it while the subsets are many enough to be fast and few enough to be fair. The number
of subsets is therefore a setting of the reconstruction like the number of iterations, and is
validated with it.

Figure [](#fig-ch28-subsets) shows what interleaved subsets look like.

```{.figure #fig-ch28-subsets src="book/figures/tikz/ch28/subsets.tex" caption="OSEM's subsets, drawn with 24 view directions in 4 subsets; MiniDAQ uses 192 views in 8. Every k-th view goes into a subset, so each subset spans the whole half turn." alt="Four circles, each crossed by six lines through its centre at angles 30 degrees apart, offset by 7.5 degrees from one circle to the next, in four colors. Labels name subset 1 with views 0, 4, 8 and so on through subset 4 with views 3, 7, 11." width="80%"}
```

## A phantom, iteration by iteration

### The data

`measurements/ch28` reconstructs a phantom on MiniDAQ's simulated scanner, with the
normalization and the background of Chapter 27: a cylinder of activity of radius 80 mm in water
of radius 90 mm, 20 MBq for 5 s, and three hot rods of radius 12, 8 and 5 mm at four times the
background's concentration. Each rod is simulated as a run of its own and added to the
background, so that the truth of each is known. The 2D sinogram is slices 20 to 74 summed, the
part of the axial field where the object is uniform along the axis: 1,044,524 prompts, of which
684,140 trues, and an additive term `b` of 366,418 counts from the randoms of the singles and the
scatter scaled to the tails. `m` is the normalization times the attenuation of the water outline.

Two numbers measure the image. The contrast recovery coefficient of a rod,
`CRC = (rod / background - 1) / (4 - 1)`, is 1 when the image has the true contrast. The noise is
the coefficient of variation of the background, its standard deviation over its mean, in a region
away from the rods.

### Contrast and noise

| Iteration | Background noise | CRC 12 mm | CRC 8 mm | CRC 5 mm |
|---:|---:|---:|---:|---:|
| 1 | 7.2% | 0.78 | 0.57 | 0.25 |
| 2 | 11.0% | 1.14 | 1.03 | 0.54 |
| 3 | 15.3% | 1.23 | 1.22 | 0.75 |
| 4 | 19.5% | 1.24 | 1.27 | 0.87 |
| 8 | 34.2% | 1.22 | 1.25 | 0.96 |
| 16 | 56.1% | 1.24 | 1.22 | 0.92 |
| 32 | 80.6% | 1.25 | 1.23 | 0.86 |

: OSEM with 8 subsets on the phantom (`measurements/ch28/reconstruct.txt`, section 2).

The large rods reach their contrast by iteration 3, the smallest by iteration 8. After that the
contrast stops changing and the noise keeps growing: four times as much at iteration 32 as at
iteration 4. This is the character of MLEM on noisy data. The early iterations recover the low
spatial frequencies, the shape of the object, and the later ones the high frequencies, which in
noisy data are mostly noise; the maximum-likelihood image of noisy counts is itself very noisy.
In practice the reconstruction is stopped early, at a number of iterations chosen for the task,
and often followed by a smoothing filter.

Figure [](#fig-ch28-montage) shows the same behaviour in images.

```{.figure #fig-ch28-montage src="book/figures/plots/ch28/montage.py" caption="A phantom like the measurement's, simulated in numpy at about its counts and reconstructed with the chapter's own projector and osem(), 8 subsets. The shape is there by iteration 2 and the small rod by iteration 4; after that, mostly noise is added." alt="Eight panels. The phantom: a disc with three bright rods of 12, 8 and 5 mm. Its sinogram: three sinusoids over a broad band. Reconstructions at iterations 1, 2, 4, 8, 16 and 32, with background noise of about 8, 11, 20, 35, 56 and 78%: the rods sharpen by iteration 4 and the background becomes grainier with every iteration." width="100%" inputs="tools/recon/mlem.py"}
```

### How certain is one image?

The CRCs above 1 look like a fault: an image should not have more contrast than the object. The
measurement checked two things before believing them.

| Realization | Background noise | CRC 12 mm | CRC 8 mm | CRC 5 mm |
|---|---:|---:|---:|---:|
| a | 19.5% | 1.24 | 1.27 | 0.87 |
| b | 20.3% | 1.11 | 0.99 | 1.03 |
| a, trues only | | 1.15 | 1.16 | 0.97 |
| b, trues only | | 1.03 | 1.02 | 1.15 |

: Two independent realizations of the phantom at iteration 4, and their trues alone (section 2b
of the measurement).

A second, independent realization of the same phantom gives 1.11, 0.99 and 1.03 at iteration 4
where the first gives 1.24, 1.27 and 0.87: a single image's CRC varies by about 0.1 from one noise
realization to the next. And the trues alone, without randoms or scatter or any estimate of
them, give the 12 mm rod a CRC 0.09 and 0.08 lower in the two realizations: that is the scatter
estimate of Chapter 27, 14% high, which takes a little too much out of the background and raises
the contrast. For the smaller rods, with fewer counts, the difference is within the noise of a
realization. The
algorithm itself recovers the contrast of noiseless data (`test_noiseless_data_give_the_object`).
One image is one sample. A claim about contrast or noise needs several realizations, or several
acquisitions of a phantom, which is what Chapter 30 does.

### The model without each correction

What each term of `m` and `b` does to the image shows when it is left out. The table gives the
background's mean in rings around the axis, each over the mean of the four rings, so that a flat
image gives 1.000 everywhere:

| Model | 0 to 10 mm | 20 to 30 mm | 40 to 50 mm | 60 to 70 mm | CRC 12 mm |
|---|---:|---:|---:|---:|---:|
| all corrections | 1.007 | 0.977 | 0.978 | 1.037 | 1.24 |
| no attenuation | 0.657 | 0.729 | 0.994 | 1.620 | 1.53 |
| no scatter | 1.091 | 1.037 | 0.977 | 0.895 | 0.82 |
| no normalization | 0.940 | 0.959 | 0.996 | 1.105 | 1.26 |
| none | 0.705 | 0.801 | 1.027 | 1.466 | 0.99 |

: The background's profile after 4 iterations of 8 subsets (section 4 of the measurement).

Without attenuation the center of a uniform cylinder comes out at 0.66 and the edge at 1.62, the
classic picture of an uncorrected PET image: the lines through the center cross the most water.
Without scatter the center is too high and the contrast too low, because the scattered counts
fill in the space between the rods. Without the normalization the profile tilts by about 16%,
following the geometric factors of Chapter 27. With all corrections the background is flat
within 4% from the center to 70 mm.

Figure [](#fig-ch28-model) draws the rows of the table.

```{.figure #fig-ch28-model src="book/figures/plots/ch28/model.py" caption="The background's profile with a correction left out of the model, from the table above. Without attenuation the centre sinks and the edge rises; without scatter the profile tilts the other way and the contrast falls." alt="Ring mean over the mean of the rings at 5, 25, 45 and 65 mm. All corrections stays near 1. No attenuation rises from 0.66 to 1.62. No scatter falls from 1.09 to 0.90. No normalization rises from 0.94 to 1.11. None rises from 0.71 to 1.47. The legend gives the 12 mm rod's contrast recovery for each." width="80%" inputs="measurements/ch28/reconstruct.txt"}
```

### When to stop, and a filter

A Gaussian post-filter trades the noise for resolution:

| Image | Background noise | CRC 12 mm | CRC 8 mm | CRC 5 mm |
|---|---:|---:|---:|---:|
| iteration 4 | 19.5% | 1.24 | 1.27 | 0.87 |
| iteration 4, 4 mm FWHM | 9.7% | 1.21 | 1.20 | 0.75 |
| iteration 4, 6 mm FWHM | 7.1% | 1.18 | 1.11 | 0.62 |
| iteration 32, 4 mm FWHM | 23.4% | 1.18 | 1.18 | 0.86 |
| iteration 32, 6 mm FWHM | 13.2% | 1.16 | 1.12 | 0.73 |

: A Gaussian post-filter (section 5 of the measurement).

A 4 mm filter halves the noise at iteration 4 and costs the smallest rod 0.12 of its CRC. Running
to iteration 32 with the same filter keeps the small rod's 0.86, at 23.4% noise, more than twice
that of iteration 4. Which
combination is right depends on what the image is for, the size of the lesions it must show and
the noise a reader accepts. It is not a software decision: the number of iterations, the subsets
and the filter are protocol settings, set and validated with the image-quality measurements of
Chapter 30 (assumption: confirm with team who owns the reconstruction protocols and how a change
to one is validated).

Figure [](#fig-ch28-crc) puts iterations and filters on one trade-off.

```{.figure #fig-ch28-crc src="book/figures/plots/ch28/crc.py" caption="OSEM on the phantom, iteration by iteration. Left, the likelihood and the noise both keep rising. Right, each rod's contrast against the noise: the contrast stops growing long before the noise does, and a post-filter (hollow markers) moves an image to the left at some cost in contrast." alt="Left: log-likelihood over iteration 1 rising steeply to about 4,000 by iteration 4 and slowly to 5,400 at 32, and background noise rising almost linearly from 7% to 81%. Right: contrast recovery against background noise for the 12, 8 and 5 mm rods; the large rods plateau near 1.23 from about 15% noise, the small rod peaks near 0.96 and falls slightly; hollow markers for filtered images sit at 7 to 23% noise with lower contrast." width="100%" inputs="measurements/ch28/reconstruct.txt"}
```

## What the tool is, and what it is not

The reconstruction in `tools/recon` is 2D, of an object uniform along the axis, without time of
flight, without a model of the detector's resolution, and in numpy. Each of those is a real
reconstruction's next step: fully 3D or rebinned data, time-of-flight kernels along each line,
resolution modeling in the system matrix, and a projector in a compiled language on many cores or
a GPU. They change the projector and the model, not the structure: a projector with its adjoint,
an update with the corrections in the model, subsets that each span the views. The tests
transfer with them, and Chapter 29 starts by moving the projector to C++ and running the same
tests on both.

::: box-regulated
- **The reconstruction makes the image.** Its output is every image, and nobody checks it pixel
  by pixel, so here it is a tool of class T3 (TL-31), qualified by its tests on known data and its
  measurements on the simulator. In a product the reconstruction is usually a software item of
  its own, with its own safety class, requirements and verification (assumption: confirm with
  team where your reconstruction sits in the architecture and which class it has).
- **A wrong model gives a plausible image.** Hazard H-13 names the ways: a backprojector that is
  not the adjoint, lines at the wrong radius, pre-corrected data, gaps read as zeros. The controls
  are tests that fail for each of them (RC-41, RC-42), and the residual is whether the model fits
  the scanner, which only phantoms show.
- **The settings are part of the device.** The number of iterations and subsets, the filter, the
  pixel size and the effective radius of the lines each change the image. Each is recorded with
  the image it made, and a change to one is a change to validate, not a configuration tweak.
- **Requirements for an algorithm are testable properties.** SRS-REC-001 to SRS-REC-003 do not say
  "the image shall be good". They say what can be checked on every build: the adjoint, the
  model, the subsets. What "good" means is the image-quality specification of Chapter 30.
:::

::: box-mistakes
- **A backprojector that is almost the adjoint.** It looks right and converges to the wrong
  image. Run the dot-product test on every change of either.
- **A constant sensitivity.** Pixels near the edge and on the lines of the gaps lie on fewer
  measured lines. Backproject `m`.
- **One angle per view.** MiniDAQ's views interleave two angles half a view apart; use each bin's
  own.
- **The lines at the front faces.** Photons interact inside the crystals. Measure the effective
  radius with a point source.
- **Correcting the data before an iterative reconstruction.** Subtracted, divided and clipped
  data is not Poisson, and its gaps are read as zeros. Put the corrections in the model.
- **Contiguous subsets, or the full sensitivity over k.** A subset must span the half turn, and
  each needs its own sensitivity.
- **More iterations are better.** After the contrast is recovered they only add noise.
- **Judging a reconstruction from one image.** The CRC of one realization varied by 0.1. Use
  several, and the noiseless case for the model.
:::

::: box-askteam
1. Which reconstruction does the product use (OSEM, a regularized method, time of flight,
   resolution modeling), in 2D, rebinned or fully 3D, and on which hardware?
2. How are the corrections passed to it: in the model, applied to the data, or some of each?
3. How was the scanner's geometry calibrated, including the depth of interaction, and where is
   the effective radius kept?
4. Which numbers of iterations and subsets, and which filters, are validated, for which
   protocols? Who may change them?
5. Does the reconstruction have a dot-product test, and does it run on every build?
6. How is the reconstruction verified against phantoms, and how often?
7. Where does the reconstruction sit in the architecture, and which safety class does it have?
:::

## Exercises {.unnumbered}

**Exercise 28.1 (M): A backprojector that is the adjoint of its projector.** *Goal:* write the
backprojection and the sensitivity that MLEM needs for a given projector, so that the pair is
exactly a matrix and its transpose. *Starter:* `exercises/ch28/e1_adjoint/starter/adjoint.py`.
*Acceptance:* `tests/test_adjoint.py` passes: the dot-product test to 1e-12, the sensitivity as
the backprojection of the multiplicative factors and smaller in a corner than at the center, MLEM
on a disc with a rising likelihood, and the true image a fixed point. Then answer in `NOTES.md`
why the disc passes with the starter, what the starter does to a corner pixel, and why OSEM needs
a sensitivity per subset. *Time:* 60 minutes.

**Exercise 28.2 (M): The corrections in the model.** *Goal:* reconstruct counts with
multiplicative and additive corrections per bin, with the corrections in the model, and measure
what correcting the data first costs. *Starter:* `exercises/ch28/e2_model/starter/model.py`.
*Acceptance:* `tests/test_model.py` passes: at low counts with many randoms the mean of 20
realizations within 3% of the truth over the object and a low background outside it, a disc with
unmeasured bins without stripes, and the counts left unchanged. Then answer in `NOTES.md` where
the clipped counts go, what MLEM believes about the gaps, and why the background outside the disc
is not 0 either way. *Time:* 60 minutes.

**Exercise 28.3 (S): Ordered subsets.** *Goal:* speed up MLEM with subsets, chosen and weighted
so that 4 iterations of 5 subsets reach what 20 iterations of MLEM reach. *Starter:*
`exercises/ch28/e3_subsets/starter/subsets.py`. *Acceptance:* `tests/test_subsets.py` passes:
the subsets hold every view once and span the half turn, impossible subsets are refused, the
true image is a fixed point, and 4 iterations of 5 subsets are within 3% rms of 20 of MLEM with
and without noise. Then answer in `NOTES.md` what uneven subsets do with the shortcut
sensitivity, why the order of the views matters, and why 192 subsets would be a bad idea.
*Time:* 45 minutes.

## MiniDAQ milestone: the reconstruction {.unnumbered}

::: box-milestone
**Goal.** `tools/recon` reconstructs a 2D image from a run with OSEM and the corrections of
Chapter 27 in its model, its projector is proven the adjoint, its geometry is measured with a
point source, and its contrast and noise are measured on a phantom. **Start:** tag `ch27`.
**End:** tag `ch28`.
:::

1. Write change request CR-0014 and ADR 0023; add SRS-REC-001 to SRS-REC-003 (SRS version 17),
   hazard H-13 with RC-41 and RC-42, and tool TL-31; update the architecture description
   (version 14).
2. Add `project.bin_lines` and `project.Projector` with the tests of class `Projection`: the two
   angles of a view, the adjoint, a disc's chords, an off-center sinusoid.
3. Add `mlem` with the tests of class `Reconstruction`: the likelihood, MLEM as one subset, the
   speed of subsets, noiseless data, unmeasured bins, the subsets.
4. Add `chain`, the corrections of Chapter 27 as steps on whole runs, and the measurement
   `measurements/ch28/reconstruct.py`, which reuses Chapter 27's runs.
5. Add Exercises 28.1 to 28.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-REC-001 to SRS-REC-003 verified; the point source comes out
within 1% of its distance from the axis at the measured radius; the phantom's background is flat
within 5% with all corrections; every starter of the chapter fails. Tag `ch28`.

## Check yourself {.unnumbered}

1. Write the model of PET data with the corrections in it. Which corrections are in `m`, which in
   `b`?
2. Why does each MiniDAQ view interleave two angles, and how far off is a line drawn at the
   view's mean angle, 100 mm from the axis?
3. Why are the lines of response deeper than the crystals' front faces, and how do you measure
   where they are?
4. What does Joseph's projector compute in each step along a line?
5. State the dot-product test. Why can a backprojector pass a visual check and fail it?
6. Write the MLEM update. Why does it keep the image non-negative?
7. What is the sensitivity image, and why is it not a constant?
8. Name two things that go wrong when the data are corrected before MLEM.
9. What does an OSEM iteration cost compared with an MLEM iteration, and what does it give?
10. Why must each subset span the half turn and carry its own sensitivity?
11. The contrast stops improving at iteration 3 and the noise keeps growing. Why?
12. A rod's CRC came out 1.24. Name two reasons it is not 1, and how the measurement found them.
13. What does a reconstruction without attenuation correction do to a uniform cylinder?
14. Which settings of a reconstruction are protocol settings to validate, and why?
15. What would you need to change to make this reconstruction 3D? What stays the same?

## Summary {.unnumbered}

- The counts of each bin are Poisson with mean `m A x + b`: the system matrix for the geometry,
  `m` for the normalization, attenuation and live fraction, `b` for the randoms and scatter.
- Each bin has its own line. MiniDAQ's views interleave two angles, and the lines are at an
  effective radius of 156 mm, not the 150 mm of the front faces: there the point source came out
  3.6% too close to the axis, at 156 mm within 0.3%.
- Joseph's projector, matrix-free, with the backprojection its exact adjoint, proven by the
  dot-product test on every build. In numpy, 54 ms forward and 44 ms back for one 2D sinogram.
- MLEM multiplies the image by the backprojected ratio of measured to expected counts over the
  sensitivity. With the corrections in the model the counts stay as measured and unmeasured bins
  take no part. Pre-corrected data biased a low-count background 2.3 times as much and turned the
  gaps into stripes.
- OSEM with 8 interleaved subsets, each with its own sensitivity, reaches in one iteration what
  MLEM reaches in 8.
- On the phantom, the contrast is reached by iteration 3 to 8 and the noise grows from 19.5% at
  iteration 4 to 80.6% at 32. One image's CRC varies by 0.1 between realizations; the scatter
  estimate adds about 0.08 to the largest rod's. The iterations, subsets and filter are protocol
  settings.
- TL-31, hazard H-13 with RC-41 and RC-42, and SRS-REC-001 to SRS-REC-003 put the reconstruction
  under the same change control as the acquisition.

## Further reading {.unnumbered}

- L. A. Shepp and Y. Vardi, "Maximum likelihood reconstruction for emission tomography", *IEEE
  Transactions on Medical Imaging* 1(2), 1982: the MLEM algorithm for emission tomography.
- K. Lange and R. Carson, "EM reconstruction algorithms for emission and transmission
  tomography", *Journal of Computer Assisted Tomography* 8(2), 1984: the derivation and the
  properties of the update, including the monotone likelihood.
- H. M. Hudson and R. S. Larkin, "Accelerated image reconstruction using ordered subsets of
  projection data", *IEEE Transactions on Medical Imaging* 13(4), 1994: OSEM, and how to choose
  the subsets.
- P. M. Joseph, "An improved algorithm for reprojecting rays through pixel images", *IEEE
  Transactions on Medical Imaging* 1(3), 1982: the projector of this chapter.
- R. L. Siddon, "Fast calculation of the exact radiological path for a three-dimensional CT
  array", *Medical Physics* 12(2), 1985: the exact intersection lengths.
- J. Qi and R. M. Leahy, "Iterative reconstruction techniques in emission computed tomography",
  *Physics in Medicine and Biology* 51(15), 2006, R541–R578: a review of the models, the algorithms
  and their noise.
- D. L. Bailey, D. W. Townsend, P. E. Valk and M. N. Maisey (editors), *Positron Emission
  Tomography: Basic Sciences*, Springer, 2005: the chapters on image reconstruction.
- The documentation of open-source reconstruction software, for example STIR and CASToR, for how a
  full 3D reconstruction with time of flight and resolution modeling is organized in its current
  release.
- ADR 0023 and CR-0014 in the repository: the decision and the change record.
