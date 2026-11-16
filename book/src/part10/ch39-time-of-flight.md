# Time of flight {#ch39}

::: box-why
Every coincidence MiniDAQ has written since version 1.0 carries the difference of its two photons'
arrival times, to the picosecond, and every reconstruction in this book has thrown it away. That
difference says where along the line of response the annihilation happened: within a few
centimeters, instead of anywhere on the chord through the patient. A reconstruction that uses it
converges faster and gives a quieter image at the same counts. It also reads meaning into a few
hundred picoseconds of the scanner's time base, the quantity Chapter 38 learned to watch. This
chapter adds time of flight to the reconstruction tool, in the numpy reference and in the C++
projector, measures what it gives on MiniDAQ's simulated scanner, and makes the tool refuse it for
a run whose clocks the monitor did not vouch for.
:::

**A day in the life.** The physicist runs the same image quality phantom twice: once without time
of flight and once with it, from the same list-mode file. The second image is visibly smoother
and its hot spheres come up after two iterations instead of four, which is what the vendor's
brochure promised. A week later, a scan of a large patient shows a faint bright streak that
crosses the liver and ends outside the body, along a line no anatomy explains. The image without
time of flight, reconstructed from the same file, shows nothing. The run's record says the time
base monitor was at alarm for 40 seconds in the middle of the scan, on six blocks fed by one
fan-out buffer. The reconstruction script had never read the record: nobody had told it that
time of flight trusts the clocks in a way that the rest of the reconstruction does not.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Place an annihilation along its line of response from the two arrival times, with the right
   factor of two and the right sign, and say what the coincidence time resolution makes of it.
2. Explain why a convention for the sign of the time difference must be fixed once, in one place,
   and tested end to end from the data to the image.
3. Write the kernel of a projector with time of flight: a Gaussian along the line, integrated over
   each TOF bin, the same in the forward and the back projection.
4. Add time of flight to a ray-driven projector without breaking its adjoint or its threads, and
   say what it costs.
5. Measure what time of flight gives: the timing resolution, the convergence and the background
   variability at equal counts, and why an unfiltered pixel can look worse.
6. Say what a clock offset does to an image with time of flight and without it, and refuse time
   of flight for a run whose time base was not shown to hold.

## Prerequisites and estimated time {.unnumbered}

Chapter 8 (time of flight in physics), Chapter 12 (the list-mode format and the histogrammer's TOF
bins), Chapter 26 (the timing calibration), Chapters 28 and 29 (OSEM and the C++ projector) and
Chapter 38 (the time base monitor). Reading: about 3 hours. Exercises: 6 hours. Milestone: 4
hours. If time is short, do Exercise 39.2.

## What time of flight adds to a line

Chapter 8 gave the physics in one sentence: an annihilation at a distance ℓ from the middle of its
line of response sends one photon a distance ℓ further than the other, so they arrive at the two
crystals with a time difference of 2ℓ / c. Turned around, a measured difference τ places the
annihilation at

ℓ = c τ / 2,

15 mm for every 100 ps. The factor of two is the first thing everybody gets wrong once: each
photon's path changes by ℓ, so their difference changes by 2ℓ.

A measured τ is not exact. Its error is the coincidence time resolution (CTR) of Chapter 8, close
to a Gaussian of a few hundred picoseconds full width at half maximum (FWHM). Along the line, that
is a Gaussian of FWHM c · CTR / 2: 45 mm for 300 ps, 75 mm for 500 ps. Without time of flight the
event is anywhere on the chord through the patient, 200 mm for MiniDAQ's phantom and 400 mm for an
adult's abdomen. With it, the event is within a few centimeters of one place on the chord.
Figure [](#fig-ch39-line) shows the difference.

```{.figure #fig-ch39-line src="book/figures/tikz/ch39/line.tex" caption="What time of flight adds to a line of response. Without it, the event is anywhere on the chord through the object; with it, the time difference τ = t~a~ − t~b~ places the event c τ / 2 from the line's middle, towards b when τ is positive, within a Gaussian of FWHM c Δt / 2 (45 mm at 300 ps)." alt="Two scanner rings side by side, each with a patient disc and a line of response between crystals a and b. Left, titled without time of flight: the whole chord through the patient is highlighted, labeled the event is somewhere on the whole chord. Right, titled with time of flight: a Gaussian curve sits on the line, centered a distance c tau over 2 from the middle towards b, with its width marked 45 mm; notes say tau equals t a minus t b, tau positive means nearer b, and a Gaussian of FWHM c delta t over 2, 45 mm at 300 ps." width="95%"}
```

What that buys is less noise. A reconstruction without time of flight must decide where along
each line its counts came from by comparing it with every other line; the noise of each line
spreads over its whole chord and adds up in every pixel it crosses. With time of flight, a line's
noise spreads over a few centimeters only. The usual estimate, Chapter 8's, is a gain in
signal-to-noise ratio of about √(D / Δx), where D is the object's size and Δx the localization:
2.1 for 200 mm and 300 ps. That is an estimate for the center of a uniform object at convergence;
this chapter measures what MiniDAQ's simulated scanner actually gives, which is less.

Time of flight does not improve the spatial resolution. A Gaussian of 45 mm says nothing about a
lesion of 5 mm that the lines' crossing angles do not already say. It changes the statistics of
the estimate, not its sharpness, and scanners with a CTR of a few tens of picoseconds, where Δx
approaches the size of a lesion, are research instruments (assumption: confirm with team what the
product's timing resolution is and how it is specified).

### What MiniDAQ already has

Most of what time of flight needs was built in earlier chapters, because the data had to carry the
time difference before anybody could use it:

- **The list mode** (MDQ-L1, Chapter 12) stores `dt_ps` for every coincidence: the later single's
  time less the earlier's, a signed integer of picoseconds. `crystal_a` is the earlier single.
- **The histogrammer** (`minidaq::sino::Histogrammer`, Chapter 12) bins τ into TOF bins with
  `minidaq_listmode sino --tof-bins K --tof-bin-ps w`, a third dimension of the sinogram.
- **The simulator** draws the time error of each pair from a Gaussian of `--ctr` FWHM, 300 ps by
  default.
- **The timing calibration** (Chapter 26) removes each crystal's fixed delay; **the time base
  monitor** (Chapter 38) watches that the blocks' clocks stay where the calibration left them.

What was missing was everything after the histogrammer: the projector of Chapters 28 and 29
spreads each line's counts over its whole length, and nothing reads the time base verdict before a
reconstruction. Change request CR-0032 and ADR 0038 add both to the reconstruction tool, `tools/
recon` (tool TL-31). None of MiniDAQ's shipped programs changes, and neither does any data format.

### List mode or sinograms

A reconstruction can use time of flight in two forms. **List mode** reconstructs event by event:
each coincidence has its own line and its own τ, and the projector evaluates a kernel centered on
exactly that τ. It is exact and it is the natural form for time of flight, but it is a second
algorithm next to the sinogram OSEM of Chapter 28, with its own subsets, its own corrections and
its own tests. **TOF sinograms** keep the histogrammer's TOF bins as a third axis: the counts of a
line in bin k are those whose τ fell in bin k, and the projector gives each step of a line a weight
for each bin. OSEM, its subsets and the corrections stay as they are; only the projector changes.

ADR 0038 takes the sinograms. The bins cost a little precision: τ is known only to the bin's
width, 100 ps or 15 mm along the line, small against the kernel's 45 mm. In exchange, the change is
confined to one class with a reference implementation and a comparison already in place (RC-43 of
Chapter 29), and the data written since 1.0 can be reconstructed as they are.

## The sign of τ

Before any kernel, a convention. A time difference has a sign, the sign says which way along the
line to go, and there are at least four places where it can be flipped: the list mode, which
stores the later time less the earlier; the histogrammer, which must decide which end of a line is
which; the projector, which walks each line in some direction; and the image, whose y axis points
up in one convention and down in another. A flip in any one of them puts every event on the wrong
side of its line's middle. The image is then still an image, with the right number of counts, of
roughly the right object, smeared in a way that looks like poor timing resolution. Nothing crashes.

MiniDAQ fixes the sign in the histogrammer and makes everything else follow it:

- Each sinogram bin has two endpoints, a and b. Endpoint a is the bin's lower transaxial crystal,
  unless the bin's angle wrapped past 180 degrees (`lor_bin()`, Chapter 12), when it is the upper.
- τ = t~a~ − t~b~, whichever single came first. A positive τ means b's photon arrived first, so the
  annihilation is nearer b.
- Bin k of K, each w wide, holds τ in [(k − K/2) w, (k + 1 − K/2) w): with K odd, the middle bin is
  centered on zero.
- Along the direction (−sin φ, cos φ) of the bin's own angle φ, endpoint a lies at negative ℓ, and
  ℓ = c τ / 2.

The last rule is the one the projector uses, and it was found, not chosen: it follows from how
`lor_bin()` numbers views and radial bins, and the end-to-end test below is what established it.
The Python binning used by the tool (`tools/recon/sinogram.py`) mirrors the histogrammer's rules,
including the integer arithmetic of the bin index, so that both put an event on a bin's edge in
the same bin:

```{.python include="tools/recon/sinogram.py" snippet="tof-bins"}
```

The list mode's `dt_ps` is always positive for a prompt coincidence (the later less the earlier),
and `crystal_a` is the earlier single, so τ is −dt when the list mode's crystal a is the
histogrammer's endpoint a, and +dt otherwise. A delayed coincidence, from the sorter's delayed
window of Chapter 10, has a second single that is 100 ns late by construction; the delay comes off
first, and what is left is spread evenly over the window, as randoms should be.

How do you test a convention? Not with a unit test of each piece against the piece's own
documentation: each piece can be right by its own description and the chain still wrong, because
the descriptions disagree. The test that settles it goes through the whole chain:
`EndToEnd.test_tof_bins_agree_with_the_histogrammer` simulates a point source at (60, −30) mm
with `minidaq_sim`, bins its list mode into 5 TOF bins of 250 ps with `minidaq_listmode sino` (the
C++ histogrammer) and with the Python binning, checks that the two agree count for count, and then
takes, for the line through the source in each view, the mean position of its counts over the TOF
bins. Against the position ℓ of the source along that line, computed from geometry alone, the
means fall on a straight line through zero. The test requires a slope within 0.08 of 0.95 (five
wide bins cut off the Gaussian's tails, which pulls the mean a little towards the middle) and
measured 0.98. A flipped sign gives −1, a missing factor of two 2 or 0.5. The test is part of the
tool's suite and runs with every build.

## A projector with time of flight

Chapter 29's `JosephProjector` walks each line of response across the image one row or column at
a time, and at each step interpolates between the two pixels that the line passes between. Time of
flight adds one quantity per step: where along the line the step is. Its walk now passes that
position, `t`, along with the pixel and its weight:

```{.cpp include="recon/src/joseph.cpp" snippet="walk"}
```

The position is linear in the step, like the fractional pixel, so it costs one multiplication
and one addition per step. It is measured from the foot of the line's normal, which is the line's
middle on the scanner: both ends of a line are on the ring, at the same distance from the center,
so the foot of the normal from the center is halfway between them.

### The kernel

For a step at t, the probability that its event lands in TOF bin j is the integral of the Gaussian
of the timing error over the bin. With the bin's edges along the line at e~j~ and e~j+1~ and σ the
Gaussian's standard deviation along the line,

p~j~(t) = ½ [erf((e~j+1~ − t) / (√2 σ)) − erf((e~j~ − t) / (√2 σ))].

Three details matter. First, σ along the line is the CTR's σ times c / 2, the same factor of two as
the position: σ = CTR / 2.3548 · c / 2, 19.1 mm for 300 ps. Second, the edges along the line are
the histogrammer's edges in τ, (j − K/2) w, times c / 2. Third, integrate, do not sample: the
density at the bin's center times its width is a fine approximation when the bins are much
narrower than the kernel and wrong when they are not (Exercise 39.2). The integral needs K + 1
calls of erf for K bins, since neighboring bins share an edge, and the probabilities of a point
well inside the bins add up to one to rounding, because the sum telescopes to the difference of
the outer two.

```{.cpp include="recon/src/joseph.cpp" snippet="kernel"}
```

The kernel only computes the bins within six standard deviations of t, where the probability is
above 10^−9^; the rest are zero. With 21 bins of 100 ps (15 mm each) and σ of 19 mm, that is about
16 bins at the middle of a line and fewer near its ends.

### Forward and back

The forward projection of a line with time of flight is K numbers instead of one: for each step,
the image value times the step's weight, spread over the bins by the step's kernel. The two pixels
of one step share its position, so the kernel is computed once per step and reused:

```{.cpp include="recon/src/joseph.cpp" snippet="tof-forward"}
```

The back projection must be its exact adjoint, or OSEM converges to something else (Chapter 28's
first lesson). For each step it forms the weighted sum of the line's K bins with the same kernel,
and adds that to the step's two pixels with their weights:

```{.cpp include="recon/src/joseph.cpp" snippet="back"}
```

The threads work as in Chapter 29: each one takes a contiguous range of lines, writes the forward
projection's lines directly (no two threads write the same line), and adds its back projection
into its own image, summed in a fixed order at the end so that the result does not depend on the
number of threads.

The numpy reference, `tools/recon/project.py`, does the same with arrays: for each view, the
position of every step of every line, one array of edges, and the kernel of every step as one
array of shape (lines, steps, K), built with an erf that numpy does not have. The tool's own,
Abramowitz and Stegun's formula 7.1.26, is within 1.5 × 10^−7^ of the exact value; forward and
back use the same values, so the adjoint holds to rounding regardless.

```{.python include="tools/recon/project.py" snippet="tof"}
```

### What the tests check

A projector with time of flight has properties that a test can check without trusting any of its
own numbers:

- **The adjoint.** For random x and y, ⟨A x, y⟩ = ⟨x, A^T^ y⟩ to 10^−6^ relative, for both
  implementations (`TofProjector.BackIsTheAdjointOfForward`).
- **The sum over TOF bins.** The K bins of a line add up to its projection without time of flight,
  for an object well inside the bins; an object near their outer edges loses its tails, as the
  histogrammer does (`TheTofBinsAddUpToTheProjectionWithoutTof`). This one test ties the new
  projector to the old, already validated one.
- **A point lies where its time of flight says.** Forward-project a single pixel at (27, −23) mm;
  in every view, the mean position over the TOF bins of the line through it is the pixel's own
  position along that line, to 1.5 mm (`APointLiesWhereItsTimeOfFlightSays`).
  Together with the end-to-end test of the binning, this fixes the sign from the data to the
  image.
- **The threads do not change the result**, and a projector with an impossible timing (zero bins,
  a negative width or resolution) is refused when it is built.
- **The numpy and C++ projectors agree** to 10^−6^ relative, in both directions, on the same lines
  (`TofSameAsNumpy`), which is RC-43 extended to time of flight.

These are SRS-REC-007's tests. OSEM itself did not change: `tools/recon/mlem.py` works on any
sinogram whose first axis is the view. The multiplicative corrections get a trailing axis
(`mult[..., None]`), and the randoms' expected counts are split over the TOF bins by the bins'
share of the coincidence window, w / W per bin, since randoms are flat in τ.

## What time of flight gives

The measurement `measurements/ch39/tof.py` uses the simulator, the Python binning and the C++
projectors of this chapter, the reconstruction of Chapter 28 with 8 subsets and 21 TOF bins of
100 ps (2.1 ns in all, 315 mm along a line, the ring's diameter), on the machine named at the top
of `measurements/ch39/tof.txt`.

### The timing resolution

First, what the simulator gives. A point source at the center, in air, for three settings of
`--ctr`:

| Set, ps FWHM | Measured, ps FWHM | Prompts |
|---:|---:|---:|
| 200 | 207 | 67,954 |
| 300 | 307 | 67,450 |
| 500 | 497 | 67,292 |

The width is that of τ over every line through the center, read from a histogram of 20 ps bins. It
is within a few percent of the set value. At 200 and 300 ps it is a little more, because the photons
interact at different depths in their crystals, which changes the path lengths of each pair; added
in quadrature, that is about 65 ps, which at 500 ps changes the width by 4 ps, less than the
histogram's bins can show. On a real scanner this is
how the CTR is measured (NEMA NU 2 specifies the details); the reconstruction needs the value, and
the timing calibration should report it (assumption: confirm with team where the product's CTR
comes from and how it is kept current).

### Noise at equal counts

Then the comparison that matters: the same data reconstructed with and without time of flight. A
uniform cylinder of radius 100 mm in air, with a rod of radius 10 mm at (50, 0) mm holding four
times the background's concentration, about 2.8 million prompts; once at 300 ps and once at 500 ps,
each its own simulation. Each iteration is measured four ways:

- the rod's **contrast recovery**, its mean over the background's, less one, divided by the true
  three, on the image after a Gaussian filter of 8 mm FWHM;
- the **noise** of the filtered image: the relative standard deviation of its background pixels;
- the **background variability** of Chapter 30: the relative standard deviation of the means of 15
  circular regions of radius 8 mm spread over the background, on the unfiltered image;
- the **pixel noise** of the unfiltered image.

At 300 ps, without time of flight and with it:

| Iteration | Contrast recovery | Noise, 8 mm filter | Background variability | Pixel noise, unfiltered |
|---:|---:|---:|---:|---:|
| 1 | 0.69 / 0.97 | 2.3% / 2.2% | 1.78% / 1.96% | 4.1% / 5.9% |
| 2 | 0.96 / 1.02 | 2.5% / 2.7% | 2.75% / 2.30% | 6.9% / 10.2% |
| 4 | 1.04 / 1.02 | 3.5% / 3.2% | 3.53% / 2.52% | 12.5% / 17.0% |
| 8 | 1.03 / 1.01 | 4.4% / 3.4% | 4.09% / 2.57% | 21.8% / 26.5% |
| 12 | 1.03 / 1.01 | 4.8% / 3.4% | 4.32% / 2.55% | 29.3% / 32.8% |

`measurements/ch39/tof.txt` has every iteration and the 500 ps run. Four things stand out.

**Time of flight converges faster.** After one iteration the rod has 97% of its contrast with time
of flight and 69% without; without, it takes three. Each event's counts start near where they
belong instead of spread over the chord, and OSEM has less to undo. For a clinical protocol this
is the first and largest effect: fewer iterations for the same contrast, or more contrast in the
same iterations (assumption: confirm with team how the product's protocol was chosen).

**At equal contrast, the background is quieter.** After 12 iterations the background variability
is 2.55% with time of flight and 4.32% without, a factor of 1.69; the filtered noise is 3.4% and
4.8%, a factor of 1.39. With time of flight both have stopped growing after about five iterations,
while without it they keep climbing. Figure [](#fig-ch39-noise) shows the background variability
at each iteration.

**The unfiltered pixel is noisier with time of flight**, at every iteration: 32.8% against 29.3% at
the twelfth. This is not a fault, and it is the trap of comparing images by one pixel's noise.
Time of flight puts more of each line's information into fewer pixels, so the image converges to
something sharper and, pixel by pixel, rougher at high frequencies, while its noise at the scale
of a lesion, which is what a filter or a region measures, is lower. Compare reconstructions at the
scale that matters for the task: a filter matched to the resolution, or regions the size of the
lesions you look for. A comparison of raw pixel noise would have concluded that time of flight
makes images worse, which is what the first version of this measurement printed.

**The gain is below the estimate.** √(D / Δx) is 2.11 at 300 ps; the measured factors are 1.39 and
1.69. The estimate is for the center of a uniform object, filtered at the localization's scale, at
convergence; a region near the edge of the cylinder has a shorter chord through it and gains less,
and the regions here are spread over the whole background. It is an estimate of the order of
magnitude, and the measurement is what goes into a document.

At 500 ps the gain shrinks, as it should: the filtered noise falls by 1.26 and the background
variability by 1.11 after 12 iterations, against an estimate of 1.63. For the first six
iterations the background variability is even higher with time of flight, because the image with
time of flight is further along in its convergence; the two curves meet at the sixth (3.00% and
2.99%) and cross before the seventh. A
comparison at equal iterations, early, would have said time of flight at 500 ps hurts; at equal
contrast, it helps a little. The two runs are separate simulations, so the images without time of
flight differ too, by their noise.

```{.figure #fig-ch39-noise src="book/figures/plots/ch39/noise.py" caption="The background variability of the cylinder at each OSEM iteration, without and with time of flight, at 300 ps and 500 ps. At 300 ps it stops growing after about five iterations with time of flight and keeps climbing without; at 500 ps the curves meet at the sixth iteration and the gain after it is small." alt="Two line plots side by side, background variability in percent against the OSEM iteration from 1 to 12. Left, timing resolution 300 ps: without TOF rises from 1.8 to 4.3 percent; TOF 300 ps rises from 2.0 to about 2.6 percent by iteration 4 and stays flat. Right, timing resolution 500 ps: without TOF rises from 1.3 to 3.5 percent; TOF 500 ps starts higher, 1.5 percent, meets the curve without TOF at iteration 6 near 3.0 percent, stays below it after, and ends at 3.1 percent." width="100%" inputs="measurements/ch39/tof.txt"}
```

The mean of the background agrees between the two reconstructions within 0.7% at 300 ps and
0.2% at 500 ps after the first iteration. That is the quantitative check that time of flight changes the
noise and not the activity: the same corrections, the same normalization, the same counts. About
5% of the prompts fall outside the 21 TOF bins; nearly all of them are randoms, whose τ spreads
over the whole 4 ns window, and the randoms estimate per TOF bin accounts for them.

## What it asks of the time base

Time of flight reads τ to a few tens of picoseconds of meaning. Everything that adds to τ and is
not the photons' paths moves events along their lines: 15 mm for every 100 ps. Chapter 26's
calibration removes each crystal's fixed delay. Chapter 38's monitor watches that the blocks'
clocks do not move during a run. What does it cost when they do?

### A clock off, in an image

The measurement simulates a point source at (40, −25) mm and then offsets the time stamps of some
blocks' singles, after the fact, as a block whose clock runs late would have stamped them:

```{.python include="measurements/ch39/tof.py" snippet="block-clock"}
```

Each case is reconstructed with 5 iterations without and with time of flight at 300 ps, and the
measure is simple: the share of the image within 8 mm of the source.

| Offset, ps | Block 29, without TOF | Block 29, with TOF | A quarter, without TOF | A quarter, with TOF |
|---:|---:|---:|---:|---:|
| 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| 100 | 100.0% | 100.0% | 100.0% | 100.0% |
| 250 | 100.0% | 100.0% | 100.0% | 99.1% |
| 400 | 100.0% | 99.6% | 100.0% | 86.0% |
| 800 | 100.0% | 99.5% | 100.0% | 82.0% |

Without time of flight, nothing happens: a few hundred picoseconds are far inside the 4 ns window,
no coincidence is lost, and the reconstruction never reads τ. With it, the answer depends on how
many lines the offset touches. Block 29 alone is one of 72 blocks, and 2% of the source's
coincidences have a single in it; moving those by 60 mm costs the image 0.4% of its counts near
the source. A quarter of the scanner, the 18 blocks that one branch of a clock tree might feed
(Chapter 38), touches 38% of the coincidences; at 400 ps the image loses 14% of its counts near the
source, at 800 ps 18%. Figure [](#fig-ch39-clock) shows both.

```{.figure #fig-ch39-clock src="book/figures/plots/ch39/clock.py" caption="The share of a point source's image within 8 mm of the source, without and with time of flight at 300 ps, against the clock offset of block 29 alone and of a quarter of the scanner. Without time of flight nothing changes; with it, an offset of a quarter of the scanner moves 14% of the image away at 400 ps." alt="Line plot of the image within 8 mm of the source, in percent, against the clock offset from 0 to 800 ps. The curves without TOF stay at 100 percent for both cases. TOF with block 29 alone falls only to 99.5 percent at 800 ps. TOF with a quarter of the scanner, 18 blocks, stays near 100 percent up to 250 ps, then falls to 86 percent at 400 ps and 82 percent at 800 ps." width="85%" inputs="measurements/ch39/tof.txt"}
```

Why only 14%, when 38% of the coincidences moved by 60 mm? Because a reconstruction does not
place each event where its τ says; it finds the image that explains all the lines together. A
displaced event's line still passes through the source, and OSEM can put activity only where some
lines agree. Part of the displaced counts goes back to the point, and the rest becomes a faint
smear along the affected lines on one side. That smear is the danger. It does not look like a
fault: it looks like activity, or like a slightly blurred lesion, in an image that is otherwise
fine. A point source in air is the easiest case; in a patient, the smear lands on tissue that has
activity of its own, and no reader can tell it apart.

The measurement also shows what does *not* happen. A single block off by 400 ps, Chapter 38's day
in the life, barely changes a point source's image, because a block holds 2% of a point's lines.
It matters more for an object near that block, whose lines through it are a larger share, and
it matters for quantitation in every case. That is why Chapter 38's limits are an assumption to
confirm for a scanner with time of flight, and why ADR 0037 says that such a scanner needs tighter
ones.

### Refusing time of flight on a time base nobody vouched for

There are two ways for the reconstruction to handle a run whose time base moved: correct the times
with the monitor's estimate of each block's offset, or refuse time of flight for that run and
reconstruct it without. ADR 0038 refuses. A correction applied to the data is a change of the
data with its own verification, the monitor's offsets are estimates with standard deviations of
tens of picoseconds per interval, and the interval in which the clock moved is not corrected by
anything. A run without time of flight is a valid run with a known, documented loss of noise
performance; a run with wrongly corrected times is an image that looks right.

The rule is in one function, which every reconstruction with time of flight goes through:

```{.python include="tools/recon/chain.py" snippet="tof-guard"}
```

Three cases refuse, each with a message that says what to do instead:

- **No verdict at all.** A run of a server before 2.0, or one whose monitor was switched off,
  carries no `timing` in its record. Nobody watched the clocks, so nobody can say they held. This
  is the case that the day in the life missed: absence of evidence treated as evidence of absence.
- **An interval at alarm.** The message names the blocks, which is what a service engineer needs
  to find the board.
- **A board's clock lost its lock** (RC-54 of Chapter 38), whatever the monitor saw. A loss of lock
  that relocked on the same phase is harmless, and the guard refuses it anyway: the record cannot
  tell the two apart.

A simulation passes: its record says so, and its clocks are what the simulator was told. The
guard is SRS-REC-008, and with the sign convention it is RC-55, a new protective measure for
hazard H-13, "a reconstruction whose model differs from the measurement", whose sequence now names
both the wrong sign of τ and a run whose block clocks moved.

Two things the guard cannot do. It cannot see what the monitor cannot: a constant offset from the
start of the run, or a shift below the warning limit. The first is the timing calibration's job,
and the daily quality control's; the second is the monitor's limits, set for a scanner without
time of flight. And it trusts the record. A record edited by hand, or written by a server whose
monitor was configured with limits so loose that nothing reaches alarm, passes. The record's
signature (Chapter 25) addresses the first; the configuration review of a protocol addresses the
second.

## What it costs

A projection with time of flight computes a kernel for every step of every line and writes K
numbers for every line instead of one. Measured on the machine of the measurement, one projection
of 128 × 128 pixels onto all 192 views, with 21 TOF bins:

| Projector | Threads | Forward, s | Back, s |
|---|---:|---:|---:|
| without TOF | 1 | 0.022 | 0.023 |
| without TOF | 4 | 0.009 | 0.007 |
| TOF, 21 bins | 1 | 0.977 | 0.983 |
| TOF, 21 bins | 4 | 0.265 | 0.294 |

About 43 to 44 times the time without time of flight on one thread. The erf calls dominate: about 17
per step, against one multiplication and one addition per pixel for the projection itself. The
forward projection scales better with time of flight on four cores (3.7 against 2.4), since there is
more work per line and the same memory traffic; the back projection, which ends by summing one image
per thread, scales about the same with and without (3.3). The sinograms are K times larger: 21
times, for a 2D sinogram of MiniDAQ's size (192 views of 227 radial bins) about 7 MB instead of 0.35
MB in double precision, and a fully 3D TOF sinogram of a clinical scanner is gigabytes.

The cost has well-known remedies, none of which MiniDAQ needs yet: tabulate the kernel once,
since it depends only on the distance from a bin's center and the bin's width (a table of a few
thousand entries, interpolated); compute it in single precision; skip the bins below a cutoff
tighter than six standard deviations; and, for list mode, evaluate one kernel per event instead
of per bin. Each is an approximation whose effect on the image must be measured, which is why the
reference implementation computes the exact integral and the faster one is compared with it.

Chapter 29's rule still holds: measure before optimizing, and keep the slow, obvious version as the
reference. The numpy projector with time of flight is far slower and is what the C++ one is tested
against, to 10^−6^.

::: box-mistakes
- **c τ instead of c τ / 2.** Every conversion from picoseconds to millimeters along a line carries
  the factor ½: the position, the resolution, the bin edges. A missing one doubles every distance
  and the image still looks plausible.
- **A sign that each piece gets right by its own description.** The list mode, the histogrammer,
  the projector and the image each have a convention; only a test from simulated data to the
  image fixes the chain.
- **The earlier single as endpoint a.** It makes the sign of τ always positive and carries the
  information in which crystal is a; the histogrammer fixes a by geometry instead.
- **Sampling the kernel at the bin's center.** Integrate over the bin; with bins as wide as the
  kernel, the sampled weights do not even add up to one.
- **A back projection that uses a different kernel from the forward.** It breaks the adjoint, and
  OSEM converges to something else, slowly enough that nobody notices.
- **Comparing raw pixel noise.** Time of flight is rougher pixel by pixel and quieter at the scale
  of a lesion; compare at equal contrast and at the scale of the task.
- **Comparing at equal iterations only.** Time of flight converges faster; early on it can look
  noisier because it is further along.
- **Splitting the randoms evenly over the TOF bins as if the bins covered the window.** Randoms are
  flat over the whole coincidence window; each bin gets w / W of them.
- **Reconstructing with time of flight because the data have τ.** The data have τ whether or not
  the clocks held; read the run's time base verdict first.
- **Correcting the times from the monitor's estimate.** That is a change of the data with its own
  verification, and it leaves the interval in which the clock moved; reconstruct without time of
  flight instead.
:::

## What this leaves out

List-mode reconstruction with time of flight, the form clinical systems use, with a kernel per
event and no binning loss; the timing resolution's dependence on the crystal pair, the energy and
the count rate, which a real reconstruction models per line; TOF scatter estimation, where single
scatter simulation must model the scattered photon's longer path; attenuation and activity
estimated together from TOF data alone (MLAA), which time of flight makes possible; the
consistency conditions of TOF data, which can find a timing offset from the data themselves;
non-Gaussian timing kernels with tails, from the electronics or the depth of interaction; and the
first TOF scanners of the 1980s, whose barium fluoride crystals had the timing and lacked the
sensitivity. The reviews by Conti, by Vandenberghe and colleagues, and by Schaart in the further
reading cover each.

::: box-regulated
- **Risk control.** ISO 14971 clause 7.1: RC-55 is a protective measure for H-13's TOF sequences;
  its effectiveness is verified by the end-to-end test of the sign and by the guard's tests. It
  relies on RC-53 and RC-54 (Chapter 38) for what they detect, and inherits their residual: a
  constant offset from the start reaches a TOF image as a displacement, controlled by the timing
  calibration of Chapter 26.
- **Requirements.** IEC 62304 clause 5.2: SRS-REC-007 (the projector's kernel, bins and sign) and
  SRS-REC-008 (the guard), each with its tests, in SRS version 35.
- **Tool validation.** The reconstruction tool is a tool, TL-31, validated for its intended use by
  its tests (ISO 13485 clause 4.1.6, Chapter 16). The tests of the TOF projector are added to its
  validation; the measurement is evidence of performance, not of correctness.
- **Change control.** CR-0032 with its impact analysis: no software item of MiniDAQ changes, no
  data format changes, and the C++ library's interface gains additions only.
- **Claims.** A claim about the image quality of time of flight in a product's labeling is a
  performance claim, made with clinical or phantom data under a standard protocol (NEMA NU 2), not
  with a simulation like this chapter's.
- **Records of this chapter.** CR-0032, ADR 0038, SRS version 35, H-13 with RC-55,
  `measurements/ch39/`.
:::

::: box-askteam
1. What is our scanner's coincidence time resolution, how is it measured, and does the
   reconstruction use one value or one per crystal pair?
2. Does our reconstruction work in list mode or with TOF sinograms? How many TOF bins, of what
   width, and why?
3. Where in our code is the sign of τ fixed, and which test goes from data to image?
4. What timing limits does our time base monitor need for time of flight, per block and per board,
   and who decided them?
5. What does our reconstruction do with a run whose time base alarmed: refuse time of flight,
   correct it, or warn? Who signs that decision?
6. How many iterations does our clinical protocol use with time of flight, and was that chosen at
   equal contrast or at equal iterations?
7. How do we compare images with and without time of flight in verification: which metric, at
   which scale?
8. What does the labeling claim about time of flight, and what data support it?
:::

## Exercises {.unnumbered}

**Exercise 39.1 (E): Where along the line.** *Goal:* place an annihilation along its line of
response from the two arrival times, and find the TOF bin the histogrammer puts it in. *Starter:*
`exercises/ch39/e1_where_on_the_line/starter/where.py`, which moves the point by c τ towards the
crystal that saw its photon first and rounds τ to the nearest bin. *Acceptance:*
`tests/test_where.py` passes: a point source anywhere inside the ring is found to 10^−6^ mm,
whichever crystal is called a; a τ beyond the line's length is clamped to the nearer crystal; the
bins of 5 × 100 ps and of 4 × 100 ps put each edge in the bin above it and τ outside every bin
gives None. *Time:* 1 hour.

**Exercise 39.2 (M): The TOF kernel.** *Goal:* the weights with which a projector with time of
flight spreads a point on a line over the line's TOF bins, checked against a simulation of the
timing error. *Starter:* `exercises/ch39/e2_tof_kernel/starter/kernel.py`, which converts
picoseconds to millimeters with c instead of c / 2 and samples the Gaussian at each bin's center.
*Acceptance:* `tests/test_kernel.py` passes: 300 ps is 19.1 mm; the probabilities of a point well
inside the bins add up to one to 10^−12^ and are symmetric for a point at the middle; with bins of
300 ps and a resolution of 100 ps, a point at the middle of a bin puts 99.96% in it; 200,000
simulated timing errors fall in the bins as the probabilities say. *Time:* 2 hours.

**Exercise 39.3 (H): Block clock offsets from a point source.** *Goal:* measure each block's clock
offset from the coincidences of a point source at a known place, the measurement behind a timing
calibration. *Starter:* `exercises/ch39/e3_block_offsets/starter/calibrate.py`, which takes the
mean τ per block and ignores the geometry. *Acceptance:* `tests/test_calibrate.py` passes, with 8
blocks on a ring of 156 mm and 40,000 coincidences at 300 ps: a source at the center, which joins
each block only to the one opposite, raises ValueError; a source 60 mm off center finds offsets of
up to 300 ps to within 8 ps; a block that saw nothing is None and the others keep a mean of zero;
swapping a and b of every event changes nothing. *Time:* 3 hours.

## MiniDAQ milestone: time of flight on a trusted time base {.unnumbered}

::: box-milestone
**Goal.** The reconstruction tool reconstructs with time of flight, in its numpy reference and its
C++ projector, with the histogrammer's bins and sign; it refuses time of flight for a run whose
time base was not shown to hold.
**Start:** tag `ch38`. **End:** tag `ch39`.
:::

1. Write change request CR-0032 and ADR 0038; add SRS-REC-007 and SRS-REC-008 (SRS version 35), and
   RC-55 to H-13 with the TOF failures in its sequence.
2. Add the TOF binning to `tools/recon/sinogram.py` and the end-to-end test of the sign against the
   histogrammer.
3. Add `TofProjector` to `tools/recon/project.py`, with its tests: the adjoint, the sum over the TOF
   bins, a point where its time of flight says, a reconstruction of noiseless data.
4. Add `recon::Tof` and the TOF walk, kernel, forward and back to `JosephProjector`; bind them as
   `recon_cpp.TofProjector`; add the C++ tests and the comparison with numpy.
5. Add `check_time_base_for_tof` and `tof_sinograms` to `tools/recon/chain.py`, with their tests.
6. Measure (`measurements/ch39/`) and add Exercises 39.1 to 39.3.

**Definition of done.** `recon_tests`, `tools.recon` and `tools.recon_cpp` pass, including the
end-to-end test of the sign; `docs.srs`, `docs.trace`, `docs.changes` and `docs.risk` pass; the
sanitizer and static analysis builds are clean; every starter of the chapter fails. Tag `ch39`.

## Check yourself {.unnumbered}

1. Derive the position of an annihilation along its line from the two arrival times. Where does
   the factor of two come from?
2. A CTR of 250 ps: what is the FWHM of the position along the line, and how many such widths fit
   across a head of 180 mm?
3. Why does time of flight not improve the spatial resolution of a clinical scanner?
4. Give two ways to use time of flight in a reconstruction, and what each costs.
5. Why is the sign of τ fixed by geometry in the histogrammer rather than by which single came
   first, and how is the whole chain tested?
6. Why is the kernel integrated over each bin rather than sampled at its center?
7. Which test ties the projector with time of flight to the one without it?
8. Why can the unfiltered pixel noise be higher with time of flight while the background
   variability is lower?
9. At 500 ps, the background variability with time of flight is higher for the first six
   iterations and lower after. Why, and what comparison avoids the confusion?
10. Why does a clock offset of one block barely change a point source's image, and why is that no
    comfort?
11. Why does the tool refuse time of flight for a run with no time base verdict, rather than
    accepting it?
12. What can the guard not see, and what controls that?

## Summary {.unnumbered}

- A time difference τ places an annihilation c τ / 2 from its line's middle, 15 mm per 100 ps,
  within a Gaussian of FWHM c · CTR / 2: 45 mm at 300 ps.
- MiniDAQ's list mode and histogrammer have carried τ since 1.0; CR-0032 adds time of flight to the
  reconstruction tool as TOF sinograms, so only the projector changes.
- The sign is fixed in the histogrammer (τ = t~a~ − t~b~, endpoint a by geometry) and tested end to
  end from a simulated point source to the projector's positions.
- The projector weights each step of a line by a Gaussian integrated over each TOF bin, the same
  in forward and back; its TOF bins add up to the projection without time of flight.
- At 300 ps, time of flight reached the rod's contrast in one iteration instead of three and
  lowered the background variability by a factor of 1.69 after twelve; at 500 ps the gain was
  1.11.
- The unfiltered pixel is noisier with time of flight; compare at equal contrast and at the scale
  of a lesion.
- A clock offset does nothing to an image without time of flight. With it, 18 blocks off by 400 ps
  moved 14% of a point's image away from the point.
- The tool refuses time of flight for a run with no time base verdict, an interval at alarm or a
  lost lock (RC-55), and reconstructs such a run without it.
- A projection with time of flight costs about 44 times one without, dominated by the erf calls.

## Further reading {.unnumbered}

- M. Conti, "State of the art and challenges of time-of-flight PET", *Physica Medica* 25(1), 2009:
  the gain, its estimate and its limits.
- S. Vandenberghe, E. Mikhaylova, E. D'Hoe, P. Mollet and J. S. Karp, "Recent developments in
  time-of-flight PET", *EJNMMI Physics* 3, 2016 (open access): detectors, reconstruction and
  clinical results.
- D. R. Schaart, "Physics and technology of time-of-flight PET detectors", *Physics in Medicine and
  Biology* 66(9), 2021: what limits the CTR and how it is measured.
- W. W. Moses, "Time of flight in PET revisited", *IEEE Transactions on Nuclear Science* 50(5),
  2003.
- S. Surti, "Update on time-of-flight PET imaging", *Journal of Nuclear Medicine* 56(1), 2015:
  the clinical evidence.
- A. Rezaei, M. Defrise, G. Bal and others, "Simultaneous reconstruction of activity and
  attenuation in time-of-flight PET", *IEEE Transactions on Medical Imaging* 31(12), 2012: what
  time of flight makes possible beyond noise.
- NEMA NU 2-2018, *Performance Measurements of Positron Emission Tomographs*: the timing resolution
  and image quality tests.
- ADR 0038, CR-0032 and `measurements/ch39/tof.txt` in the repository.
