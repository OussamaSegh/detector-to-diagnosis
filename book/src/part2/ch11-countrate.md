# Count-rate performance and dead time {#ch11}

::: box-why
A clinical PET scan starts with a dose of a few hundred megabecquerels. The activity in the
field of view is highest right after injection, and it falls over the hours that follow. The DAQ
has to behave predictably across all of that range, and it has to say how it behaved. Two
numbers decide whether it does: the count-rate curve, which shows how many usable
coincidences come out at each activity, and the activity at which some part of the chain
saturates first. Both depend on the detector, the sorter's windows and the software. Both are
measured with a standard test (NEMA NU 2) that physicists, regulators and competitors all
read. This chapter models the front end's dead time and pile-up and computes the
noise-equivalent count rate. It uses that rate to choose the windows, then finds which part
of MiniDAQ saturates first and at which rate. The goal is that "it keeps up" becomes a curve
with a peak and a margin.
:::

**A day in the life.** The physicist plans the first count-rate test on the new scanner. A
line source of fluorine-18 will start at 600 MBq and decay overnight, and the DAQ will
acquire for twelve hours. Two days before the test, someone asks you two questions. Will the
DAQ keep up at the start? And will the counters say so if it does not? You have numbers for
neither. You set up a dead-time model of the front end, using the 1 µs per block the
electronics engineer quoted. You simulate the test with the NEMA phantom from 5 to 1000 MBq,
replay the simulated singles through the acquisition software at their real rate, and read
the utilization of every stage. The software saturates at about 70 M singles per second,
more than the front end can deliver at any activity. The Gigabit link from the readout
board saturates first, near 115 MBq, and the network counters of Chapter 9 would report it
as lost packets. The scanner's NECR peaks near 70 MBq. So the test will start with the link
losing packets for the first four hours or so. That is visible, but not catastrophic. You add a second link to the board's
configuration, write down the activity at which each stage saturates, and attach the model to
the test plan. The lesson of this chapter: know which part of the chain gives first, and at
which activity, before the measurement starts.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Model paralyzable and non-paralyzable dead time and pile-up, predict their effect on the
   recorded rate, and correct a measured rate for them.
2. Compute the noise-equivalent count rate (NECR) and the scatter fraction, explain why the
   NECR peaks, and use it to choose the coincidence time window and the energy window.
3. Explain what the NEMA NU 2 tests measure (sensitivity, count rate and scatter fraction,
   spatial resolution, image quality, the accuracy of corrections) and what the DAQ must
   provide for each. Explain when NU 4 applies instead.
4. Measure which stage of an acquisition chain saturates first as the activity rises (link,
   sorter, disk) and write it up as a throughput budget with margins.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (the pipeline and its latency report), Chapter 8 (trues, scatters and randoms,
the simulator), Chapter 9 (the link budget) and Chapter 10 (the sorter, its windows and its
multiples policies). Reading: about 3 hours. Exercises: 11 hours. Milestone: 4 hours. In the
10-week schedule this chapter fills the second half of week 4.

## Dead time and pile-up

### The intuition

A detector channel is not ready all the time. After a photon arrives, the channel spends a
while integrating the scintillation light, digitizing the pulse and handing the event on.
That time is its *dead time* τ. A second photon that arrives in that time cannot be
recorded as an event of its own. Either it is lost, or its light adds to the pulse being
integrated and changes the first event's energy, which is *pile-up*. At 1,000 photons per
second and τ = 1 µs, a channel is busy 0.1% of the time and nobody notices. At 500,000 per
second it is busy half the time, and the recorded rate no longer grows with the activity.

How much of the scanner shares one dead time matters as much as τ. If each crystal had its
own electronics, the rate per channel would be tiny. MiniDAQ's ring has 18,432 crystals, and
at 100 MBq of the NEMA-style source each one sees about 900 singles per second. Readout
electronics usually multiplex, though: a block of crystals shares a light-sharing readout or
an ASIC, and an event anywhere in the block makes the whole block busy. MiniDAQ has 72
blocks of 256 crystals, so the same 100 MBq gives each block about 230,000 singles per second.
With a 1 µs block dead time that is a busy fraction near 20%. Which unit shares a dead time,
and how long it lasts, is a property of the NeuroLF's front end that you must ask about
(assumption: confirm with team). This chapter uses a 1 µs block dead time to show the
effects, not to predict the real scanner.

### Two models

Two idealized models bracket real electronics, and both go back to the counting statistics
of Geiger counters (Knoll, Chapter 4).

- **Non-paralyzable.** A recorded event makes the unit dead for τ. Events that arrive in
  that time are lost and do not extend it. A unit that sees a Poisson stream of true rate n
  records, on average, m = n / (1 + nτ). The recorded rate grows without bound towards 1/τ,
  one event per dead time.
- **Paralyzable.** Every arriving event, recorded or not, makes the unit dead for τ from its
  own arrival time. An event is recorded only if nothing arrived in the τ before it, which
  for a Poisson stream has probability e^(−nτ), so m = n e^(−nτ). The recorded rate rises to
  a maximum of 1/(eτ) at n = 1/τ, then falls. A fast enough stream keeps the unit dead
  indefinitely.

Electronics whose busy period is set by a fixed conversion time behave like the first.
Electronics that must see the signal drop below a threshold before accepting a new pulse
behave like the second, because a pulse that arrives in the tail of the previous one keeps
the signal up. Real front ends are often a mixture of both, and their behavior is measured,
not assumed.

![Left: recorded against true rate for one unit with Poisson arrivals, in units of 1/τ. The
paralyzable curve has a maximum of 1/e at nτ = 1, and every lower recorded rate belongs to
two true rates. Right: the share of singles lost with a 1 µs dead time per block in
MiniDAQ's simulator, against the models evaluated at the average singles rate per
block.](src/img/ch11-deadtime.png){width=100%}

The two models agree to first order: for nτ ≪ 1 both give m ≈ n(1 − nτ). They part ways
above nτ ≈ 0.2. The right half of the figure shows something the formulas alone do not. The
simulated losses are higher than the models predict from the average block rate: 20.9%
against 18.8% for the non-paralyzable model at 100 MBq. The line source sits 45 mm off the
axis, so the blocks do not share the load evenly. At 100 MBq they see between 122,000 and
421,000 singles per second. The number of events a block loses, n²τ/(1 + nτ), grows faster
than linearly with its rate, so the busy blocks lose more than the quiet ones save. Applied
to each block's own rate and summed, the models give 20.9% and 23.5%, exactly the
simulated losses. A dead-time correction that uses the scanner's average rate per unit
instead of each unit's own rate underestimates the loss, and more so the further the
activity is from the center.

### A worked example

Take one block at n = 500,000 singles per second with τ = 1 µs, so nτ = 0.5.

- Non-paralyzable: m = 500,000 / 1.5 = 333,000 per second; a third of the events are lost.
- Paralyzable: m = 500,000 × e^(−0.5) = 303,000 per second; 39% are lost.

A coincidence needs both of its singles. If the two blocks are independent and both at this
rate, a coincidence survives with probability about (m/n)², or 44% and 37%. The measured
coincidence rates show this square law. With the 1 µs block dead time at 100 MBq, and pile-up
switched off, 20.9% of the singles are lost and the trues fall from 90,700 to 59,300 per
second. That is 65% of them, against (1 − 0.209)² = 63%
(`measurements/ch11/frontend.txt`). The small difference comes from blocks whose rates differ,
the same effect as in the figure.

### Pile-up

When a lost event's light adds to the event being recorded, the recorded event has the
wrong energy. A 511 keV photon with a 200 keV Compton deposit on top of it becomes a 711 keV
event, above a 585 keV upper threshold, and the true it belonged to is gone. Two scattered
photons of 250 keV each make a 500 keV event inside the window. So pile-up removes trues and
adds scatters, and it does both more as the rate rises. MiniDAQ's model is the worst case:
it adds the whole energy of every lost event, where a real pulse adds only the part of its
light that falls inside the integration window. Even so, the effect is the largest single
term in the count-rate loss of this chapter:

| Front end at 100 MBq | Singles lost | Trues/s | Scatter fraction | NECR (k = 1) |
|:---------------------|-------------:|--------:|-----------------:|-------------:|
| no dead time | 0% | 90,733 | 0.332 | 40,746 |
| 1 µs per crystal, with pile-up | 0.1% | 90,473 | 0.332 | 40,613 |
| 1 µs per block, no pile-up | 20.9% | 59,267 | 0.327 | 26,741 |
| 1 µs per block, with pile-up | 20.9% | 38,433 | 0.395 | 15,271 |

: What each part of the front-end model costs at 100 MBq of the NEMA-style source
(`measurements/ch11/frontend.txt`; 1 µs non-paralyzable dead time, the harness's sorter).

The same dead time per crystal costs nothing measurable. Per block, it costs a third of the
NECR, and pile-up costs more than 40% of what is left. The scatter fraction, which NEMA measures at
low activity precisely because it should not depend on the rate, rises from 0.33 to 0.40.
That is why the readout architecture (how many crystals share a channel, and how the
channel rejects pile-up) sets the count-rate performance of a scanner long before the
software does.

::: box-mistakes
- **One dead time for the whole scanner.** The rate per unit, not the total, sets the loss.
  A correction computed from the total singles rate underestimates the loss in busy units,
  and more so for an off-center source.
- **Treating paralyzable and non-paralyzable as the same.** They agree at low rate, which is
  where most tests run. They differ by tens of percent near saturation, which is where it
  matters.
- **Ignoring pile-up because the loss counter looks fine.** Pile-up loses no events. It
  changes energies, so it shows up as a scatter fraction that grows with the rate, not as
  a lost count.
:::

### MiniDAQ's dead-time stage

`sim::DeadTime` applies a dead-time model to the simulator's time-ordered singles before
they are sorted. It plays the part of the front-end electronics, so it belongs in the
simulator, not in the acquisition pipeline:

```{.cpp include="minidaq/include/minidaq/sim/dead_time.hpp" snippet="config"}
```

The stage keeps one busy state per unit. An event that arrives while its unit is busy is
lost. With pile-up its energy is added to the event the unit is recording, and in the
paralyzable model it restarts the dead time:

```{.cpp include="minidaq/src/sim/dead_time.cpp" snippet="push"}
```

Two details make the stage exact rather than approximately right. First, a recorded event
cannot be released downstream as soon as it arrives, because a later event on the same unit
may still pile up on it. The stage holds every recorded event until its unit has been idle
for τ. It releases held events strictly in arrival order, so the output stays time-ordered
even when an early event on a busy unit waits longer than a later one on another unit.
Second, the boundary is explicit. The dead time is the half-open interval [t, t + τ), so an
event at exactly t + τ is recorded. The tests (SRS-DTM-001 to 008) check both models by hand
and against the formulas on Poisson streams. They also check that chunking the input does
not change the output, and that every single is counted as recorded or lost.

### Correcting for dead time

Correction inverts the model, from the recorded m back to the true n:

```{.cpp include="minidaq/src/sim/dead_time.cpp" snippet="theory"}
```

The non-paralyzable inverse has a closed form, n = m / (1 − mτ), and exists only for
m < 1/τ. The paralyzable one does not, short of the Lambert W function. On the branch
n < 1/τ the curve is increasing and concave, so Newton's method from n = m climbs
monotonically to the root. Above the maximum 1/(eτ) there is no solution, and the function
returns NaN rather than a number that looks plausible.

The correction also amplifies the uncertainty of the measured rate. A relative error ε in m
becomes (m/n)(dn/dm) ε in n. For the non-paralyzable model the factor is 1 + nτ; for the
paralyzable one it is 1/(1 − nτ), which grows without bound at the maximum, where the
recorded rate no longer depends on the true one (Exercise 11.4). At nτ = 0.5 the factors are
1.5 and 2. A corrected rate is only as good as the τ it assumes and the side of the maximum
it assumes, which is why NEMA measures the accuracy of the count-loss correction as a test
in its own right.

## Count rates and the NECR

### What is counted

Chapter 8 split the prompt coincidences into three kinds by their truth: *trues* T (both
photons from one annihilation, neither scattered), *scatters* S (one annihilation, at least
one photon scattered, so the line of response is wrong) and *randoms* R (two annihilations).
On a real scanner the truth is not known. Randoms are estimated from a delayed window or
from the singles rates (Chapter 10). Scatters are estimated from the counts outside the
object, or with a model of the scatter physics. MiniDAQ's simulator knows the truth, so the
count-rate harness classifies every prompt the sorter finds by looking its two singles up
in the simulator's record (`minidaq_sim`, the `classify` snippet of Chapter 10).

The *scatter fraction* SF = S / (T + S) leaves the randoms out. It describes the
object and the energy window, not the rate, so the standard measures it at low activity.

### The noise-equivalent count rate

More prompts do not mean a better image. Each scatter puts counts on the wrong line, and
each random adds counts that must be estimated and subtracted, adding their noise without
adding signal. The noise-equivalent count rate expresses all of that as one number:

  NECR = T² / (T + S + kR)

It is the rate of trues of a hypothetical noise-free acquisition that would give the same
signal-to-noise ratio as the real one (Strother, Casey and Hoffman, 1990). The intuition is
in the variance. The trues are what you want. Their estimate is the prompts minus the
estimated randoms and scatters, and with Poisson counting its variance is the sum of the
counts that went into it. If the randoms are subtracted with a delayed window, whose counts
are as noisy as the randoms themselves, the randoms contribute twice, and k = 2. If the
randoms estimate is smooth (computed from the singles rates, or a variance-reduced delayed
estimate), it adds almost no noise, and k = 1. NEMA NU 2 has used both conventions over its
editions (verify: the k and the randoms estimate that the edition you report against
prescribes). A count-rate curve is meaningless without its k.

```{.cpp include="minidaq/include/minidaq/processing/count_rates.hpp" snippet="rates"}
```

A worked example, from the harness at 100 MBq without dead time: T = 90,733, S = 45,080 and
R = 66,233 per second. Then T + S + R = 202,046 and NECR (k = 1) = 90,733² / 202,046 =
40,745 per second, within rounding of the 40,746 the harness prints. With k = 2 the
denominator is 268,279 and the NECR is 30,686. Of the 202,046 prompts per second, the image
gets the statistical value of 40,745 noise-free trues.

### The count-rate curve

`measurements/ch11/countrate.py` is MiniDAQ's count-rate harness. For thirteen activities
from 5 to 1000 MBq and three front-end models, it runs `minidaq_sim --nema 1` with 10 to
15 million decays per point. It sorts with a 4 ns window, a 435 to 585 keV energy window, the
kill-all multiples policy, sectors at least one apart and a 120 mm field of view. It prints
the trues, scatters, randoms, scatter fraction and NECR. The source is a 1.6 mm radius, 700
mm long line 45 mm off the axis of a 203 mm diameter, 700 mm long water cylinder, after the
NEMA count-rate phantom (verify: the dimensions against the NU 2 edition in use). Most of its
700 mm lies outside MiniDAQ's 118 mm axial field of view, as it would in a brain scanner.

![NEMA-style count-rate curves from MiniDAQ's simulator. Left: trues, scatters and randoms
without dead time (solid) and with a 1 µs non-paralyzable dead time per block and pile-up
(dashed). Right: NECR for the three front ends, k = 1 solid and k = 2
dashed.](src/img/ch11-countrate.png){width=100%}

| Front end | Peak, k = 1 | At | Peak, k = 2 | At |
|:--------------------------|---------:|--------:|---------:|--------:|
| no dead time | 73,500/s | 560 MBq | 43,600/s | 430 MBq |
| 1 µs non-paralyzable per block, pile-up | 16,100/s | 73 MBq | 12,700/s | 63 MBq |
| 1 µs paralyzable per block, pile-up | 15,500/s | 67 MBq | 12,300/s | 58 MBq |

: NECR peaks of the count-rate harness (`measurements/ch11/countrate.txt`), interpolated with
a parabola in ln(activity) through the best point and its neighbors (Exercise 11.1), so the
activities are approximate.

Three things stand out. Without dead time the randoms overtake the trues near 140 MBq and
grow as the square of the activity, while trues and scatters grow linearly. The dead-time
front end moves the peak down by almost an order of magnitude, from about 560 to about
70 MBq, and lowers it to about a fifth. And k = 2 lowers every peak and moves it to a lower
activity, because it doubles the weight of the randoms.

### Why the NECR peaks

The plan's first check-yourself question has a subtle answer, so work through it. Suppose
the trues grew exactly as aA with the activity A, the scatters as bA and the randoms as cA².
Then

  NECR = a²A² / ((a + b)A + kcA²) = a²A / (a + b + kcA),

which rises towards a limit a²/(kc) and never falls. For this phantom a = 9.07 × 10^−4^ trues
per second per becquerel and c = 6.6 × 10^−12^ randoms per second per becquerel squared, so the
limit is about 124,000 per second for k = 1. Randoms alone flatten the curve. They do not
bend it down.

The curve falls because the trues grow more slowly than the activity, for any reason at
all. Without dead time, the sorter's kill-all policy discards every window with three or
more singles, and there are more of those as the rate rises. At 1000 MBq the harness counts
a third fewer trues per decay than at 100 MBq. With a dead time, each single survives with
some live fraction L, which falls with the rate. A true needs two singles, so T ∝ A L², and a
random needs two singles too, so R ∝ A² L². Where the randoms dominate, NECR ≈ T² / (kR) ∝
A² L^4^ / (A² L²) = L². So past the peak, the NECR falls as the square of the live fraction,
and pile-up, which removes trues from the energy window, makes it fall faster still.

So the short answer is this: the NECR peaks because something loses trues faster than the
activity adds them, while the randoms keep the denominator large. Dead time, pile-up and
multiples rejection are those losses.

The peak tells you how to use the scanner. Above the peak, more activity gives a worse
image and more radiation dose for the patient and the staff. Clinical protocols are
designed to stay below it. A DAQ that keeps up with the detector at every activity up to
well past the peak is enough. A faster one buys nothing the image can use.

::: box-mistakes
- **Comparing NECR curves with different k.** A k = 2 curve is lower and peaks earlier than
  the k = 1 curve of the same data. Always state k and how the randoms were estimated.
- **Reading the scatter fraction from a high-activity acquisition.** With pile-up it grows
  with the rate. Measure it where dead time and randoms are negligible, as the standard does.
- **Too few counts per point.** At the dead-time peak the harness counts only about 7,500
  trues per point: a 1.2% statistical uncertainty. Report the counts behind each point,
  as `countrate.txt` does in its `T n` column, before comparing two curves to the percent.
:::

## Choosing the windows

### The time window

The NECR is the number that chooses the coincidence window. A wider time window keeps trues
whose photons arrive further apart, but it opens more time for randoms, and the randoms grow
linearly with its width. A narrower one does the opposite. `measurements/ch11/windows.py`
sweeps both windows at 30 and 100 MBq with the dead-time front end.

![NECR (k = 1) against the coincidence time window (left) and the lower energy threshold
(right), at 30 and 100 MBq with the 1 µs block dead time and pile-up. The dotted lines mark
the harness's 4 ns and 435 keV.](src/img/ch11-windows.png){width=100%}

| Time window | Trues/s | Randoms/s | NECR (k = 1) |
|------------:|--------:|----------:|-------------:|
| 0.5 ns | 38,767 | 4,000 | 22,216 |
| 1 ns | 39,433 | 8,013 | 21,249 |
| 2 ns | 39,067 | 16,447 | 18,822 |
| 4 ns | 38,433 | 33,207 | 15,271 |
| 8 ns | 37,227 | 64,467 | 11,016 |

: The time window at 100 MBq, energy window 435 to 585 keV (`measurements/ch11/windows.txt`).

The randoms double with every doubling of the window, as R = 2τS~1~S~2~ says. The trues barely
change. Narrowing the window from 4 ns to 1 ns raises the NECR by 39% at 100 MBq and by 11% at
30 MBq, and costs no trues at all. The trues even rise slightly as the window narrows,
because fewer windows hold three singles and the kill-all policy discards fewer of them.

Why are the trues all inside 1 ns? Light travels 300 mm per nanosecond. For an annihilation
at distance r from the scanner's center, the two photons' paths differ by at most 2r, so
their arrival times differ by at most 2r/c plus the detector's time resolution. The line
source is 45 mm off the axis, so its trues arrive within 0.3 ns of each other, smeared by
the simulator's 300 ps FWHM coincidence time resolution. An object filling MiniDAQ's 120 mm
radius field of view would need 0.8 ns plus a margin for the resolution. The window a
scanner needs is set by the diameter of its field of view and its time resolution. It is not
set by habit. In MiniDAQ the window τ is the largest accepted time difference, so pairs with
|Δt| ≤ τ pass; some vendors quote the full width 2τ instead (verify: the NeuroLF's
convention).

### The energy window

The energy window trades the other way. A higher lower threshold rejects photons that lost
energy by Compton scattering in the patient, so it cuts scatters. But with a finite energy
resolution it also rejects some unscattered 511 keV photons, and those are trues. It also
cuts the singles rate, and with it the randoms.

| Lower threshold | Trues/s | Scatters/s | Randoms/s | SF | NECR (k = 1) |
|---------:|---------:|---------:|---------:|------:|---------:|
| 350 keV | 40,640 | 55,087 | 52,947 | 0.576 | 11,109 |
| 400 keV | 39,040 | 36,780 | 40,333 | 0.485 | 13,122 |
| 435 keV | 38,433 | 25,087 | 33,207 | 0.395 | 15,271 |
| 460 keV | 36,273 | 17,380 | 27,500 | 0.324 | 16,213 |
| 480 keV | 29,553 | 10,653 | 20,173 | 0.265 | 14,465 |

: The lower energy threshold at 100 MBq, time window 4 ns, upper threshold 585 keV
(`measurements/ch11/windows.txt`).

With the simulator's 12% FWHM energy resolution, the NECR is best near 460 keV at both
activities. Raising the threshold from 435 to 460 keV gains 6% at 100 MBq and 6.5% at 30 MBq.
Beyond that the photopeak itself is cut, and at 480 keV the trues fall by 23% from their
value at 435 keV.

### Which window matters more

This is the plan's second check-yourself question, and the measurements answer it for this
system. At high activity the time window matters much more: randoms grow as the square of
the activity and linearly with τ, so the window that controls them gains more as the
activity rises. Between 4 ns and 1 ns the NECR gains 39% at 100 MBq. The best energy
threshold gains 6%, about the same at both activities, because the scatter fraction depends
on the object, not on the rate. At low activity, where randoms are few, the two are
comparable: 11% and 6.5% at 30 MBq.

The answer depends on the detector. A better time resolution allows a narrower window. A
better energy resolution sharpens the photopeak and moves the best threshold up. The
NeuroLF's own resolutions move both optima (assumption: confirm with team). The method
carries over even where the numbers do not. Sweep each window, plot the NECR, and choose the
window from the curve, at the activity the protocol uses.

::: box-mistakes
- **Choosing the window from the trues alone.** The widest window keeps the most trues and
  gives the worst NECR. The trues are the numerator, not the answer.
- **Choosing it at one activity.** The best time window narrows as the activity rises. Check
  the choice at the clinical activity, not only in a low-activity calibration.
- **Changing a window without the corrections.** Scatter and randoms corrections, and the
  normalization, are calibrated for a window. A new window needs them recalibrated and the
  change recorded with the data.
:::

## NEMA NU 2 and what it asks of the DAQ

### The standard

NEMA NU 2, *Performance Measurements of Positron Emission Tomographs*, is the standard that
manufacturers use to specify a clinical PET scanner. Its 2018 edition is the current one at
the time of writing (verify: the edition the NeuroLF's documentation cites). It does not set
limits. It defines how each figure of merit is measured, so that two scanners measured by it
can be compared. For small-animal scanners, NEMA NU 4-2008 defines the same kinds of tests
with phantoms the size of a mouse and a rat. A brain-dedicated scanner sits between the two.
Its ring is smaller than a whole-body scanner's, and the NU 2 phantoms may not fit or may not
represent a head. Which edition, and which adaptations, the NeuroLF's performance is
specified with is a question for your team (assumption: confirm with team).

The standard's text is copyrighted, and this book does not reproduce it. What follows is the
shape of each test in general terms, and what the DAQ must provide for it. When you run or
analyze a test, work from the standard itself.

### The tests

- **Spatial resolution.** Point sources at several positions in the field of view are
  reconstructed with a specified algorithm. The width of the point-spread function is
  reported as its full width at half and at tenth maximum, radially, tangentially and axially
  (verify: the positions and the reconstruction NU 2-2018 prescribes). The DAQ must deliver
  unfiltered list-mode or sinogram data and the exact crystal and time information the
  reconstruction needs.
- **Sensitivity.** A line source is measured inside a series of metal sleeves of increasing
  thickness, and the count rate is extrapolated to zero attenuation (the method of Bailey et
  al., 1991). The result is counts per second per unit of activity, at the center and off the
  axis (verify: the off-axis position). The DAQ's rates must be correct at low activity, with
  dead time and randoms negligible or corrected.
- **Scatter fraction, count losses and randoms.** This is the count-rate test of this
  chapter. A long line source in a cylindrical phantom starts at high activity and is
  measured repeatedly as it decays, so one fill gives the whole curve. From each
  acquisition's sinograms, the trues are separated from the scatters and randoms using the
  counts outside a band around the source, and the randoms from the delayed window or the
  singles. The results are the trues, scatter, randoms and NECR curves, the peak NECR and its
  activity, and the scatter fraction (verify: the band width and the randoms estimate
  NU 2-2018 prescribes). The DAQ must record every acquisition with its activity, start time
  and duration, its counters (singles, prompts, delayed, losses), and its window settings.
  Those are the counters and the configuration record of Chapter 10.
- **Accuracy of corrections.** From the same data, the standard measures how well the
  scanner's own dead-time and randoms corrections recover the true rate across the activity
  range, as a residual error per slice. This is where the correction of this chapter, and its
  error amplification near saturation, is tested.
- **Image quality and the accuracy of attenuation and scatter corrections.** A body-shaped
  phantom with hot and cold spheres in a warm background, and a lung insert, is imaged with
  the clinical protocol. Contrast recovery and background variability are reported (verify:
  the phantom and the activity ratios). Every correction of the chain is in this result.
- **Time-of-flight resolution.** The 2018 edition added a measurement of the coincidence
  time resolution of time-of-flight scanners (verify). The DAQ must deliver each
  coincidence's time difference at full resolution.

### What MiniDAQ's harness is and is not

The harness is a NEMA-*style* count-rate test, and the difference matters. It uses the shape
of the NEMA phantom and source, sweeps the activity, and reports the same curves. But the
rates come from the ground truth, not from the sinogram analysis the standard prescribes.
The phantom is water rather than polyethylene, the scanner is MiniDAQ's model ring, and the
dead time is an assumption. Its value is different: it tells you what the DAQ does to the
curve. Because the truth is known, it separates the losses of the front end, the sorter's
policy and the windows. A real measurement cannot. On the real scanner, the same harness
run on a simulation of the NeuroLF front end predicts the test before it is run, and
explains it afterwards.

## The end-to-end throughput budget

### The chain

Between the crystal and the disk, an event passes through a chain of stages. Each one has a
capacity:

1. **The front end** records singles with its dead time. This is the detector's limit, and
   no software changes it.
2. **The readout link** carries the singles to the acquisition computer. Chapter 9 computed
   14.8 M singles per second for one Gigabit link at 182 words per packet, and 148 M for
   10 GbE.
3. **The acquisition software** decodes, time-orders and sorts them. Its capacity is
   measured, below.
4. **Memory**, between the stages. Each single is copied a few times on its way through the
   rings of the pipeline. At 70 M singles per second and 8 bytes each, a copy is
   560 MB/s, well within one core's memory bandwidth but not free once several stages and the
   writer share it.
5. **The disk** stores the coincidences, not the singles. At 400 MBq without dead time the
   harness counts about 1.4 M prompts per second, and the delayed coincidences of the randoms
   estimate add more. The list-mode format of Chapter 12 decides the bytes per event.

The *load* on each stage grows with the activity in its own unit: singles per second for
the link and the sorter, bytes per second of coincidences for the disk. A budget compares
them at the activity they share. A comparison of capacities directly is meaningless,
because the units differ (Exercise 11.5).

### Measuring the software

A software stage's capacity cannot be read from a benchmark of its inner loop. It depends
on the data (here, how many singles pass the energy window and how many windows hold several
singles), on the other stages sharing the machine, and on the batching. Measure it in the
running pipeline, with realistic data.

MiniDAQ does that with two tools. `sim::ReplaySource` delivers a recorded stream (the
simulator's output for the NEMA-style source, written with `minidaq_sim --words`) on the
same wall-clock schedule as Chapter 4's paced source. When the recording ends it starts
again, with every time stamp shifted by the recording's length, so the stream stays in time
order for as long as the run lasts. `minidaq_latency --words FILE` runs the pipeline with that
source. After its latency table, it prints how busy each stage was: the sum of its batch
service times over the wall time. It also prints how often each stage stalled on a full
output queue or idled on an empty input, and how much the source dropped.
`measurements/ch11/bottleneck.py` sweeps the activity:

| Activity | Singles/s | Dropped (%) | Decode (%) | Sort (%) | Pair (%) | p99 (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 20 MBq | 3.3 M | 0 | 1.4–1.6 | 3.5–3.7 | 4.0–4.2 | 1.3 |
| 100 MBq | 16.7 M | 0 | 6.7–6.8 | 19.1–19.6 | 22.9–23.0 | 1.0–1.7 |
| 200 MBq | 33.4 M | 0 | 10.8–11.0 | 35.5–36.6 | 45.3–45.7 | 0.8–2.1 |
| 300 MBq | 50.1 M | 0 | 15.1–15.4 | 50.9–53.4 | 70.2–72.9 | 1.5–5.0 |
| 400 MBq | 66.8 M | 0.06–0.17 | 19.0–19.8 | 68.1–69.0 | 97.3–97.5 | 6.5–12.3 |

: Busy percentages of MiniDAQ's stages, and the end-to-end latency's 99th percentile, with the
NEMA-style stream replayed in real time, two runs of 3 s per activity, no dead time
(`measurements/ch11/bottleneck.txt`; Xeon at 2.30 GHz, 4 vCPU, GCC 13.3, -O2; the write
stage discards its input and stays at or below 0.1%).

The pair stage, the coincidence sorter, saturates first. Its busy percentage grows linearly
with the rate. Fitted through the origin over the whole sweep, it reaches 100% at about
70 M singles per second, or 420 MBq of this source (Exercise 11.3). At 400 MBq it is 97% busy,
the source starts to drop words, and the end-to-end latency's 99th percentile jumps from
about 2 ms to about 10 ms as the queues fill. The sort stage is next, at about 96 M singles
per second. The replay source's own busy time, 23% at 20 MBq and about 65% from 100 MBq up,
is the work of reading the clock and copying, not a limit of the pipeline. A real source is
a network card, so it is left out of the analysis.

Compare the capacity with Chapter 10's benchmark with care. There the sorter alone took
68 M singles per second, 31 M of them inside the energy window. Here about 63% of the
singles fall outside the window, so the pair stage's 70 M is only about 26 M inside it. Both
the offered and the accepted singles cost time, and in the pipeline five threads share four
cores. A capacity measured in one setting carries over to another only with the data mix
and the machine that go with it.

### The budget

| Stage | Capacity, singles/s | Full at, no dead time | Full at, 1 µs per block |
|:------|------:|------:|------:|
| NECR peak | | 560 MBq | 70 MBq |
| one Gigabit link | 14.8 M | 89 MBq | 115 MBq |
| one 10 GbE link | 148 M | 886 MBq | never |
| pair stage (sorter) | 70 M | 420 MBq | never |
| sort stage | 96 M | 570 MBq | never |

: The throughput budget of MiniDAQ for the NEMA-style source. Without dead time the singles
rate is 0.167 per decay; with the 1 µs block dead time and pile-up it is the recorded rate of
`countrate.txt`, which never exceeds 49 M per second up to 1000 MBq. The activities are
approximate, read from the measured curves; the link capacities are from Chapter 9.

Read it from the top. The detector's dead time puts the NECR peak near 70 MBq, so no
clinical protocol needs much more. The dead time also caps the singles the front end can
deliver, here below 49 M per second, which this sorter can always keep up with. One
Gigabit link would saturate at about 115 MBq, just past the peak. That is too close, because
a count-rate test starts far above the peak. With a 10 GbE link, or several Gigabit links,
nothing in the software saturates with this front end. Without the dead time, the sorter
would be the first software limit, at about six times this NECR peak. Keep a margin on
every stage: 30% is a common rule, which makes the sorter "full" at about 290 MBq. A faster
front end is what would bring it into play. The disk is not in this table,
because its load depends on the list-mode format, which Chapter 12 defines. The method of
Exercise 11.5 adds it with a single line.

A budget like this is a design document. It says which stage to watch when the scanner
changes: a faster front end moves the peak up and brings the link and the sorter closer.
Write down its assumptions (machine, build, data, dead time), as Chapter 3's performance
report did, and repeat the measurement when any of them changes.

::: box-mistakes
- **Measuring capacity with synthetic data.** Uniform random energies put a different share
  of singles in the energy window than a patient does, and the sorter's work depends on that
  share. Replay a realistic stream.
- **Reading busy percentages of a source you control.** A replay or test source does its own
  work, which is not a limit of the pipeline. Leave it out, or measure the real interface.
- **Budgeting the average.** Rates are not uniform in time either. The first minutes after
  injection, and a bolus passing through the field of view, are the peak. Budget for the peak,
  with a margin, and make the counters report when the margin is gone.
:::

::: box-regulated
Count-rate performance is part of the device's specified performance, and the DAQ produces
the data it is measured from.

- **The performance specification is a requirement.** Peak NECR, its activity, the
  scatter fraction and the accuracy of the dead-time and randoms corrections are stated in
  the device's technical documentation and verified with the standard's tests. The DAQ
  settings used for that verification (windows, policy, dead-time correction) are the ones
  the device ships with, and a change to them is a change to verified performance (IEC 62304
  change control, Chapter 14).
- **Corrections are software with requirements.** The dead-time correction, its valid range
  and its behavior above the maximum (MiniDAQ returns NaN, not a guess) are requirements
  with tests (SRS-DTM-001 to 008, SRS-CNT-001). What the device does when the correction is
  out of range is a hazard question for the risk file (ISO 14971, Chapter 15).
- **Saturation must be visible.** A stage that cannot keep up must say so in its counters
  and in the acquisition record, so that a scan acquired past a limit can be recognized
  afterwards. The budget's margins, and how they were measured, belong in the verification
  records.
- **Simulations support, they do not replace.** A NEMA-style simulation is evidence for
  design decisions. The device's performance claims come from measurements made as the
  standard prescribes (verify: what your quality system accepts as verification evidence for
  performance claims).
:::

::: box-askteam
1. What is the NeuroLF's dead time, per what unit (crystal, block, ASIC, board), and is it
   closer to paralyzable or non-paralyzable? How is pile-up rejected or corrected?
2. Which NEMA standard, edition and adaptations are the NeuroLF's performance specified
   with, and what are its peak NECR, the activity at the peak and its scatter fraction?
3. Which coincidence time window and energy window are used clinically, how was the choice
   made, and is the window quoted as τ or as 2τ?
4. Which NECR convention (k = 1 or 2) and which randoms estimate do the team's count-rate
   reports use?
5. Which stage of the real chain saturates first today (front end, link, sorter, disk), at
   what activity, and how would the operator know?
:::

## Exercises {.unnumbered}

**Exercise 11.1 (M): Count-rate curves and the NECR peak.** *Goal:* measure trues,
scatters, randoms, the scatter fraction and the NECR against activity with MiniDAQ's
simulator, with and without dead time, and find the activity of the NECR peak. *Starter:*
`exercises/ch11/e1_count_rate/` (an NECR that is not squared, a front end applied after
sorting, scatters counted as trues, and the best sample reported as the peak).
*Acceptance:* `tests/test_count_rate.cpp` passes: the NECR and scatter fraction by hand; the
peak of A·exp(−A/100) found within 6 of 100 from samples at 30, 60, 120 and 240; a scatter
fraction between 0.30 and 0.40 at 20 MBq; trues multiplied by 1.7 to 2.3 and randoms by 3.0
to 5.2 from 50 to 100 MBq; with the 1 µs block dead time, less than 70% of the trues at
100 MBq and an NECR peak between 40 and 200 MBq. Then plot the curves from a full sweep and
answer, in `NOTES.md`, why the curve without dead time still peaks. *Time:* 3 hours.

**Exercise 11.2 (M): Dead time and pile-up in a block detector.** *Goal:* add a dead-time
model to the simulator's output, one dead time per block, non-paralyzable or paralyzable,
with optional pile-up, and check the recorded rate against the two models. *Starter:*
`exercises/ch11/e2_dead_time/` (the models swapped, an event at exactly t + τ lost, no
pile-up, and a theoretical recorded rate equal to the true rate). *Acceptance:*
`tests/test_dead_time.cpp` passes: hand-made streams for both models, the boundary, blocks
that are independent, and pile-up; Poisson arrivals at 5 M per second on one block with
τ = 100 ns within 1% of both formulas; on 3 ms of simulated 30 MBq data with τ = 1 µs and
pile-up, exactly the singles of `sim::DeadTime` for both models. Then plot recorded against
true rate and explain the two branches of the paralyzable model in `NOTES.md`. *Time:* 2
hours.

**Exercise 11.3 (H): Find the first bottleneck.** *Goal:* raise the rate through MiniDAQ's
pipeline until something gives, find which stage gave first, at which rate and how you
know, and document it as a measurement report. *Starter:* `exercises/ch11/e3_bottleneck/`
(Python; a parser that reads only the first stage, the replay source counted as a limit,
drops ignored, and a capacity from the last point alone). *Acceptance:*
`tests/test_bottleneck.py` passes: a real `minidaq_latency` report parsed into its rates
and five stages, with the latency table left out; no saturation at 50 MBq, where the pair
stage is the busiest real stage at 9.7%; the pair stage saturated at 400 MBq and not at
300 MBq; fitted over the chapter's sweep, capacities of 69.82 M singles per second for the
pair stage and 95.85 M for the sort stage. Then run the sweep on your machine and write the
report in `NOTES.md`. *Time:* 4 hours, half of it measuring.

**Exercise 11.4 (E, extra): Correcting a measured rate for dead time.** *Goal:* invert both
models, with the paralyzable model's two branches and its maximum, and derive how much the
correction amplifies the uncertainty of the measured rate. *Starter:*
`exercises/ch11/e4_dead_time_correction/` (Python; a wrong sign, a first-order guess for the
paralyzable model, and no error amplification). *Acceptance:* `tests/test_correction.py`
passes: round trips to nine digits from 1,000 to 900,000 per second with τ = 1 µs; the
non-paralyzable case by hand; 2.3646 M per second on the high branch for the recorded rate
of 300,000 per second; NaN above 1/(eτ); amplification factors of 1.5 and 2.0 at 500,000 per
second that agree with a numerical derivative; a simulated unit corrected to within 1%.
*Time:* 1 hour.

**Exercise 11.5 (E, extra): An end-to-end throughput budget.** *Goal:* write the chain's
budget as code. Give each stage a load that grows with the activity in its own unit, then
find which stage saturates first and where, with and without a margin. *Starter:*
`exercises/ch11/e5_throughput_budget/` (Python; the preamble and inter-frame gap forgotten,
utilization upside down, the margin added to the capacity, and the bottleneck chosen by the
smallest capacity). *Acceptance:* `tests/test_budget.py` passes: 14.79 M singles per second
for one Gigabit link; saturation by hand, with a margin and never; with one Gigabit link
the link first at 88.6 MBq, although the writer has the smallest capacity number; with
10 GbE the sorter first at 407.2 MBq, or 285.0 MBq with a 30% margin; a disk load that more
than doubles from 200 to 400 MBq. *Time:* 1 hour.

## MiniDAQ milestone: a count-rate test harness {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ produces NEMA-style count-rate curves. It has a front-end dead-time and
pile-up model, the NECR and scatter fraction, a harness that sweeps the activity, a window
study, and a measurement of which software stage saturates first with a realistic stream.
**Start:** tag `ch10`. **End:** tag `ch11`.
:::

1. Add `sim/dead_time.hpp` and `.cpp`: `DeadTimeModel`, `DeadTimeUnit`, `DeadTimeConfig`,
   `validate`, the analytical `recorded_rate` and `true_rate`, and the `DeadTime` stage with
   `DeadTimeStats`, with `test_dead_time.cpp` (SRS-DTM-001 to 008).
2. Add `processing/count_rates.hpp` with `CountRates` (prompts, scatter fraction, NECR for a
   given k) and `test_count_rates.cpp` (SRS-CNT-001).
3. Give `minidaq_sim` the options `--deadtime`, `--tau`, `--pileup`, `--deadtime-unit` and
   `--nema`, a dead-time line in its report and one `countrate` line for scripts.
4. Add `sim/replay_source.hpp` (`ReplaySource`, with `test_replay_source.cpp`, SRS-SIM-020
   and 021). Give `minidaq_latency` the options `--words` and `--speed`, and print the
   per-stage utilization table after the latency table.
5. Add `measurements/ch11/countrate.py`, `windows.py`, `frontend.py` and `bottleneck.py`,
   with their results committed next to them.

**Definition of done.** `ci/run_all.sh` is green on all six presets;
`tools/static_analysis.sh` reports nothing; the dead-time stage matches both formulas on
Poisson streams and gives the same output however its input is chunked; each measurement is
regenerated by one command, and its header names the machine and the seed; the count-rate
curves show a peak for every front end, and the bottleneck table names the first stage to
saturate. Tag `ch11`.

## Check yourself {.unnumbered}

1. Why does NECR peak and then fall? What would it do if the trues grew exactly in
   proportion to the activity?
2. What changes NECR more: a narrower time window or a narrower energy window? Does the
   answer depend on the activity?
3. A block records 400,000 events per second with τ = 1 µs. What is the true rate under each
   model? For the paralyzable model, is there another one?
4. Why does the dead time per block cost a third of the NECR at 100 MBq, while the same dead
   time per crystal costs nothing measurable?
5. Pile-up loses no events. How does it still lower the NECR, and which measured number
   shows it?
6. Derive the error amplification 1/(1 − nτ) of the paralyzable correction. What happens at
   nτ = 1?
7. NECR is T²/(T + S + kR). Where does k = 2 come from, and when is k = 1 right?
8. Why does the line source of the NEMA-style phantom need only a 0.5 ns window in MiniDAQ,
   and what would a head filling the field of view need?
9. Why is the scatter fraction measured at low activity?
10. The replay source is 65% busy and the pair stage 45% at 200 MBq. Which is the
    bottleneck, and why?
11. One Gigabit link, a sorter at 70 M singles per second and a writer at 5 M coincidences
    per second: which saturates first for the NEMA-style source, and why is comparing the
    three capacities the wrong way to find out?
12. Name two things a count-rate measurement on the real scanner tells you that MiniDAQ's
    harness cannot, and one thing the harness tells you that the measurement cannot.

## Summary {.unnumbered}

- A non-paralyzable unit records n/(1 + nτ); a paralyzable one records n e^(−nτ), at most
  1/(eτ), and has two true rates for every lower recorded rate.
- The unit that shares a dead time matters as much as τ: 1 µs per block loses 21% of the
  singles at 100 MBq, and 1 µs per crystal loses 0.1%.
- A coincidence needs two live singles, so coincidence losses go as the square of the live
  fraction; pile-up adds losses of its own and raises the scatter fraction.
- Corrections invert the models. They amplify errors by 1 + nτ or 1/(1 − nτ), and must
  refuse rates above the maximum.
- NECR = T²/(T + S + kR) is the rate of noise-free trues with the same signal-to-noise
  ratio; state k (2 for a delayed-window subtraction, 1 for a smooth estimate).
- Randoms alone only flatten the NECR curve. It peaks and falls because trues are lost faster
  than the activity adds them: dead time, pile-up and multiples rejection.
- The NECR chooses the windows. Here 1 ns instead of 4 ns gains 39% at 100 MBq, while the best
  energy threshold gains 6%. The time window matters more as the activity rises.
- NEMA NU 2 defines how sensitivity, count rate, resolution, image quality and corrections
  are measured; the DAQ must record counters, settings and timing with every acquisition.
- MiniDAQ's first software bottleneck is the sorter's pair stage, at about 70 M singles per
  second (420 MBq of the NEMA-style source), far beyond the front end's NECR peak near 70 MBq.
- A throughput budget compares stages at the activity they share, keeps a margin, and names
  its assumptions.

## Further reading {.unnumbered}

- National Electrical Manufacturers Association, *NEMA NU 2-2018: Performance Measurements
  of Positron Emission Tomographs*, NEMA, 2018; and *NEMA NU 4-2008: Performance
  Measurements of Small Animal Positron Emission Tomographs*, NEMA, 2008.
- S. C. Strother, M. E. Casey and E. J. Hoffman, "Measuring PET scanner sensitivity:
  relating countrates to image signal-to-noise ratios using noise equivalent counts", *IEEE
  Transactions on Nuclear Science* 37(2) (1990) 783–788 (verify: the citation details).
- G. F. Knoll, *Radiation Detection and Measurement*, 4th ed., Wiley, 2010: Chapter 4 on
  counting statistics and dead time.
- S. R. Cherry, J. A. Sorenson and M. E. Phelps, *Physics in Nuclear Medicine*, 4th ed.,
  Elsevier Saunders, 2012: the chapters on PET performance and count-rate behavior.
- D. L. Bailey, T. Jones and T. Spinks, "A method for measuring the absolute sensitivity of
  positron emission tomographic scanners", *European Journal of Nuclear Medicine* 18 (1991)
  374–379 (verify: the citation details).
- D. L. Bailey, D. W. Townsend, P. E. Valk and M. N. Maisey (eds.), *Positron Emission
  Tomography: Basic Sciences*, Springer, 2005: the chapter on performance evaluation.
