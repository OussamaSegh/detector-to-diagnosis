# Corrections: normalization, randoms, scatter, attenuation, dead time and decay {#ch27}

::: box-why
A PET image is meant to show activity, in becquerels per milliliter, and a scanner counts
coincidences. Between the two lie six corrections. Each crystal detects with its own efficiency,
random pairs and scattered photons add counts that carry no information about the line, the
patient absorbs most photon pairs before they leave the body, the electronics miss events at high
rates, and the tracer decays while you count. None of these corrections is computed in the DAQ
software. The physicists compute them, from what the acquisition recorded, and each one fails
quietly if a number it needs is missing or belongs to another scan. This chapter builds the
inputs into MiniDAQ (a singles counter and a record of the settings) and a corrections tool in
Python that computes each correction and measures it against the simulator's truth. You will see
an estimator that was 31% wrong for a reason that is a rule of your own sorter, a fit that
estimated 2.4 times the true scatter, and the check that stops a normalization from correcting a
scan taken with other settings.
:::

**A day in the life.** On Monday the clinical team reports that since last week the brain images of
one scanner show a faint pattern of rings and a slightly hot center, and the quality-control
phantom shows it too. Nothing in the DAQ's logs is wrong. The physicist finds the reason by Tuesday:
a new protocol lowered the energy window's lower edge from 435 to 410 keV to gain sensitivity, and
the normalization scan, the measurement of each crystal's efficiency, was taken a month ago with
the old window. A crystal's efficiency depends on the window, because a crystal with a lower gain
loses a different share of its events at the edge, so the old normalization no longer divides out
the new data's pattern. The fix takes a day: every run record now names its energy window,
coincidence window, window mode and calibration table, and the corrections tool refuses a
normalization whose settings differ from the run's and names each difference. The physicist adds
a normalization scan to the protocol change's checklist.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Write the measurement model of a PET line of response, prompts equal efficiency times
   attenuated trues plus scatter, plus randoms, and derive the order in which the corrections are
   applied.
2. Say what each correction needs from the acquisition, add those inputs to a streaming pipeline
   and a run record, and tie a correction to the data it corrects.
3. Estimate randoms from the delayed window and from singles rates, and explain why the singles
   estimate must leave out singles that the sorter already paired.
4. Compute a component-based normalization from a normalization scan, and say how many counts it
   needs for a given precision.
5. Compute a calculated attenuation correction, fit a scatter estimate to the tails of a
   projection, and explain where each one fails.
6. Correct for dead time from per-block singles rates, and for decay over a frame.
7. Verify a chain of corrections against a known truth, and place the corrections tool, its
   inputs and its models in a regulated life cycle.

## Prerequisites and estimated time {.unnumbered}

Chapter 8 (PET physics: annihilation, Compton scatter, attenuation), Chapter 10 (the coincidence
sorter, its windows and the kill-all rule), Chapter 11 (count rates and dead time), Chapter 12 (the
list-mode file, its run record and the sinogram) and Chapter 26 (calibration). You
need Python 3 with numpy. Reading: about 3 hours. Exercises: 4 hours. Milestone: 6 hours. If time
is short, do Exercises 27.1 and 27.2.

## From counts to activity

### The measurement model

Take one line of response, one bin of a sinogram. During a scan it records P prompt coincidences.
Some are true: both photons came from one annihilation on the line and reached their crystals
without scattering. Some are scattered: one photon or both changed direction in the patient, so the
line the scanner records is not the line the annihilation was on. Some are random: two photons of
different annihilations arrived within the coincidence window. On average,

$$P = n \, (A \, L \, T + S) + R$$

where T is what you want, the true coincidences that a perfect scanner would record from the
activity along the line, and

- n is the normalization: the efficiency of the line, the product of its two crystals' detection
  efficiencies and a geometric factor (solid angle, angle of incidence, the axial position of the
  line);
- A is the attenuation: the probability that both photons leave the body, exp(-mu l) integrated
  along the line;
- L is the live fraction: the share of the coincidences that the electronics were not busy for;
- S is the scatter, before the normalization (assumption: confirm with team whether your scanner's
  scatter model includes the normalization or not; a model that works in normalized units divides
  the data by n before it subtracts S, as MiniDAQ's tool does);
- R is the randoms, which arrive after the normalization: they are already counts of the scanner's
  own crystals.

Solve for T and you have the order of the corrections:

$$T = \frac{(P - R) / (n \, L) - S}{A}$$

Subtract the randoms, divide by the normalization and the live fraction, subtract the scatter,
divide by the attenuation, and finally multiply by the decay factor, which turns the counts of the
frame into counts at the reference time. A reconstruction that models the data statistically puts
these factors into its system model instead of applying them to the data (Chapter 28), but it
needs the same numbers.

### What each correction needs

| Correction | Needs from the acquisition | MiniDAQ records it in |
|---|---|---|
| Randoms | each crystal's singles in the energy window, or the delayed coincidences; the coincidence window | the run record (`corrections`); the list mode (delayed flag) |
| Normalization | a normalization scan with the same energy window, coincidence window and calibration | the normalization scan's own run record |
| Scatter | the prompts outside the object (the tails); the energy window, for the scatter model | the list mode; the run record |
| Attenuation | the outline of the object, or a CT or MR image | outside the DAQ |
| Dead time | each block's rate of singles of every energy | the run record (`corrections`) |
| Decay | the start and length of the frame, the tracer | the run record (times); the protocol |

: What each correction needs, and where MiniDAQ records it.

Until this chapter the run record had the counters of the link and the stages, and the
configuration, but not the singles rates or the windows. Without them a randoms estimate from the
singles is impossible, the dead-time correction has no rate to start from, and nothing ties a
normalization to the runs it may correct.

### The singles counter

The decode stage already passes every single through the calibration and the photopeak monitor
(Chapter 26). One more line counts them:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="decode-count"}
```

The counter keeps two kinds of count, because two corrections need different singles. The randoms
come from singles that could have made a coincidence, so per crystal it counts the singles inside
the sorter's energy window, after calibration. Dead time comes from everything that kept a block
busy, so per block it counts every valid single whatever its energy:

```{.cpp include="minidaq/include/minidaq/processing/singles_counter.hpp" snippet="counter"}
```

It has one writer, the decode thread, so each count is a relaxed atomic load and store rather than
a read-modify-write; any thread may take a snapshot, which is exact once the pipeline has stopped
(SRS-COR-001). On the pipeline benchmark of Chapter 5 its cost was not measurable: 27 to 28 M
singles/s with it and 22 to 29 M without, the spread between runs of the same build
(`measurements/ch27/singles-counter-cost.txt`).

At the end of the run the service adds the counts and the sorter's settings to the run record:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="corrections-record"}
```

```{.cpp include="minidaq/src/control/corrections_record.cpp" from="nlohmann::json corrections_record" to="}  // namespace"}
```

The 18,432 counts go into the record only, not into the status that a client polls every second.
The record is the contract with the corrections tool: version 3 of the MDQ-L1 specification
describes the `corrections` object, and a reader that does not know it ignores it (SRS-COR-002).

## The corrections tool

### Reading the list mode in Python

The corrections are the physicists' code, and in most teams it is Python. MiniDAQ's tool,
`tools/recon`, uses numpy only, as `tools/calib` does: it is a tool whose output becomes part of
the image (TL-30, class T3), and every library it uses would be one more item to qualify. Its
reader is the second independent reader of MDQ-L1, after the crash tool of Chapter 12. It checks
the file's magic, version and header CRC, each block's CRC and sequence number, and reads the
records as one numpy structured type:

```{.python include="tools/recon/listmode.py" snippet="record"}
```

A reader that skips the checks would read a damaged block as coincidences; this one raises
`FormatError` and names the block, and its test damages a block to prove it.

### Binning that agrees bin for bin

The tool bins the coincidences into the sinogram of Chapter 12 itself, because the corrections
work per crystal and per bin and need to know which crystal pair each bin holds. In MiniDAQ's
sinogram each view and radial bin holds exactly one transaxial pair of crystals:

```{.python include="tools/recon/sinogram.py" snippet="pairs"}
```

Two implementations of one binning are two chances to disagree. The test `EndToEnd` runs
`minidaq_sim`, bins its list mode with `minidaq_listmode sino` (the C++ histogrammer) and with the
Python tool, and requires the two to be equal in every bin, and the five truth sinograms to add up
to the prompts. A test that compares two implementations finds the disagreements that a test of
each against its own expectations would miss: a rounding of the radial coordinate, a wrapped view,
a ring pair counted in the wrong slice.

### The simulator's truth

A correction measured against itself proves nothing. `minidaq_sim` knows what each coincidence
was, so with `--truth-sino PREFIX` it writes the prompts, delayeds, trues, scatters and randoms as
separate sinograms through the same histogrammer, and the truth file of the crystals gains each
crystal's efficiency (`--efficiency-spread`, SRS-SIM-023). The measurement of this chapter,
`measurements/ch27/corrections.py`, simulates a scanner whose crystals detect with efficiencies
spread by 5%, a normalization scan of a cylinder in air, and a phantom: a uniform cylinder of
activity of radius 80 mm in a water cylinder of radius 90 mm, a model of a head, at 20 MBq for
5 s. Each correction is compared with the truth.

## Randoms

### Two estimators

A random coincidence is two singles of different annihilations within the window. For two crystals
with singles rates s_a and s_b and a coincidence window of tau, a single of crystal a pairs with any
single of crystal b in the 2 tau around it, so the rate of randoms is

$$R_{ab} = 2 \, \tau \, s_a \, s_b$$

The factor 2 is the commonest mistake: the other single may come before or after. A scanner
estimates the randoms in one of two ways:

- **The delayed window.** The sorter opens a second window, shifted by 100 ns, far longer than any
  true pair's time difference. Nothing true falls in it, and on average it records as many randoms
  as the prompt window. MiniDAQ's sorter has had it since Chapter 10.
- **The singles rates.** Count each crystal's singles and compute `2 tau S_a S_b / t` for every
  pair, with S the singles of the run and t its length. No second window, and no noise of its own,
  since each crystal has thousands of singles.

### The singles that were already paired

The first version of the tool computed the singles estimate as written. It was 31% too high:

```{.text include="measurements/ch27/corrections.txt" from="Run: 5.000 s" to="Per bin:"}
```

The reason is a rule of MiniDAQ's own sorter. A single that is part of a prompt coincidence cannot
also be part of a random pair: if a third single falls into the pair's window, the window holds
three singles, and the kill-all rule of Chapter 10 discards all of them; if not, the single is
used. Either way, the paired singles add no randoms, and here 13.5% of the singles were paired.
Taking each crystal's prompt coincidences off its singles before the product leaves -1.8%:

```{.python include="tools/recon/corrections.py" snippet="randoms"}
```

The same reasoning has a name in the literature, a correction of the singles estimate for the
singles that are in coincidence (verify: the published method and its derivation before you rely
on it; see Further reading). What matters for you is the lesson: an estimator that is correct in a
textbook is wrong for a sorter whose rules it ignores, by an amount that depends on the count rate.
The delayed window, which goes through the same sorter, is 7.1% high, the kill-all bias that Chapter
10 measured: a random that the kill-all rule discards from a prompt window, because the window
also held the true partner, is still counted in the delayed window of the same opener.

### Noise

Randoms are few per bin. In this run there were 0.028 per bin on average, and a sinogram bin almost
always held 0 or 1 delayed coincidence. Subtracting the raw delayeds bin by bin is unbiased and adds
the full Poisson noise of the delayeds to the data, 0.175 rms on a mean of 0.028. The singles
estimate has none of that noise. A scanner that relies on the delayeds smooths them first: the
randoms of a line factorize into a value per crystal, and each crystal's fan sum of delayeds
determines its value. Exercise 27.2 builds that variance reduction and shows why the textbook
formula fails on a scanner whose crystals meet only part of the ring.

## Normalization

### Efficiencies and geometry

The normalization n of a line is everything that makes it count differently from its neighbor for
the same activity. A direct measurement of every line needs a normalization scan of hundreds of
millions of counts. A component-based normalization splits n into factors that are each measured
with far fewer: each crystal's efficiency, and geometric factors that are the same for every view
of a ring scanner. MiniDAQ's tool measures both from one scan of a cylinder of activity in air that
fills the field of view.

A crystal's efficiency comes from its fan sum, the coincidences it took part in (prompts minus
delayeds, to remove the randoms):

```{.python include="tools/recon/corrections.py" snippet="fansum"}
```

For a centered cylinder every crystal of a ring sees the source alike, so a fan sum over its
ring's mean is the crystal's efficiency relative to its ring. The ring's own mean is left to the
geometric factors, which hold what remains of the scan once the efficiencies and the source's
chords are divided out:

```{.python include="tools/recon/corrections.py" snippet="geometric"}
```

Exercise 27.1 builds the general form, for a source that not every crystal sees alike, and shows
why the one-step ratio works for MiniDAQ and not for a small scanner.

### How many counts

```{.text include="measurements/ch27/corrections.txt" from="6 runs:" to="## 2."}
```

The crystals' efficiencies came out 3.4% rms wrong per crystal, the Poisson error of fan sums of
1,040 counts (3.1%) plus a little. A bin's efficiency is the mean over the ring pairs of the bin's
slice, so the errors of many crystals average out and the bin's efficiency was 1.4% wrong. For 1%
per crystal the scan needs 10,000 counts per crystal, 92 million coincidences for 18,432 crystals,
about 260 s at 10 MBq in the simulation. A real normalization scan takes hours (assumption: confirm
with team how long yours is and how often it is repeated).

### A normalization belongs to its settings

A crystal's efficiency is not a property of the crystal alone. It is the share of its photons that
end up in the data, and that depends on the energy window (a crystal with a lower gain or a worse
resolution loses a different share at the window's edges), on the coincidence window and its mode,
and on the calibration table. The day in the life's normalization was measured with a lower edge of
435 keV and applied to data taken at 410 keV. So the tool compares the two run records before it
normalizes anything:

```{.python include="tools/recon/corrections.py" snippet="compatible"}
```

It refuses a normalization with another energy window, coincidence window, window mode or
calibration table, or with no `corrections` object at all, and names each difference
(SRS-COR-003). This is a risk control (RC-40), and the run record's settings are what make it
possible (RC-39).

## Attenuation

### Wherever along the line

Both photons of a pair must leave the body. If one travels a and the other b through tissue of
attenuation coefficient mu, the pair survives with probability exp(-mu a) exp(-mu b) =
exp(-mu (a + b)), and a + b is the whole chord through the body, wherever on the line the
annihilation was. That is why attenuation correction in PET is a factor per line, exp(mu L) for a
uniform medium, and why it is large: water at 511 keV has mu = 0.096 per cm (verify: NIST XCOM),
so a line through the center of a head of 18 cm is corrected by exp(1.73) = 5.6.

MiniDAQ's tool models the phantom as what it is, a water cylinder, and averages over the ring
pairs of each slice, whose oblique lines cross more water:

```{.python include="tools/recon/corrections.py" snippet="attenuation"}
```

### The outline is a model

A cylinder of water is not a head. A scanner with a CT uses the CT image, converted to attenuation
coefficients at 511 keV; a scanner without one models the head from the emission data or an MR
image, as an outline filled with water plus, at best, a skull (assumption: confirm with team which
attenuation correction your scanner uses). An outline 5 mm too large all round adds 10 mm of water
to a central line, exp(0.096) = 1.10: 10% too many counts on that line. Exercise 27.3 computes the
attenuation of an elliptical outline, off center and turned, and the error of a circle in its
place. The attenuation model is part of the residual risk of H-12: no test of the software can tell
whether the outline is the patient's.

## Scatter

### The tails

A scattered coincidence lies on a line that misses the annihilation, so scatter fills in the
projection smoothly, inside and outside the object. Outside the object there are no trues, only
scatter and randoms; with the randoms subtracted, what is left in the tails is scatter. Tail
fitting uses that: fit a shape to the tails and extend it under the object.

The classic shape is a Gaussian in s. It failed:

```{.text include="measurements/ch27/corrections.txt" from="True scatter fraction" to="Each cell"}
```

The Gaussian fitted to the tails was 33 mm wide and gave 2.4 times the true scatter under the
object, almost 4 times at the center. The tails of this phantom are short: the water ends at
90 mm, the field of view at 113 mm, and the scatter that the energy window keeps falls off within
about 15 mm of the water's edge, because a photon that scattered enough to land far outside the
object lost too much energy to pass the window. A Gaussian narrow enough to fall off that fast is
too peaked inside. The shape has to come from a model of the object: a single scatter simulation
from the activity and attenuation images, or a Monte Carlo (assumption: confirm with team which
scatter model your reconstruction uses). The measurement uses the simplest model there is, the
same phantom simulated on a perfect scanner, its scatter averaged over the views, and scales it to
the tails:

```{.python include="tools/recon/corrections.py" snippet="tails"}
```

### The fit that ran low

The first version of the scale was a least-squares fit to the normalized data, and it gave 0.78
times the true scatter, even in the tails it was fitted to. The model's shape was right: its tails
over its interior matched the truth's within 1%. The fault was the fit. In the end slices of the
scanner, where few ring pairs contribute, the normalization is a few percent of the center's, and
such a bin holds 0 counts most of the time and 1/n now and then. Least squares weighted those bins
as much as the central ones, and the scale became an average of huge values and zeros, unbiased in
theory and badly noisy in practice. The scale is now the Poisson maximum likelihood: the counts in
the tails over the counts the shape predicts there, `sum(P) / sum(n S)`. A unit test with bins of
sensitivity 0.01 to 1 checks that its error is the Poisson error of the tail counts; the
least-squares fit is 1.5 times as noisy on the same data.

### What the tails cannot do

The table shows the two limits that remain. The tails hold nearly six randoms for each scatter
count (23,976 against 4,173). The singles estimate of the randoms is 2.3% low there, and those 544
counts become scatter: 1.14 times the true scatter. With the true randoms subtracted the model's
estimate is 1.01. And one slice's tails hold about 66 scatters among 431 prompts, so a scale per
slice is 42% noisy; one scale for all slices is 14% per slice, at the cost of assuming that the
model's axial shape is right. A real patient's tails are also cut by the bed and the shoulders. A
scatter correction is a model with a measured scale, and both the model and the scale need
validation with phantoms (Chapter 30).

## Dead time and decay

### Dead time

A block that is busy with one event misses the next (Chapter 11). For a non-paralyzable dead time
tau and a recorded rate m, the true rate is n = m / (1 - m tau), so the live fraction m / n is
1 - m tau; for a paralyzable unit m = n exp(-n tau), which the tool solves for n below the maximum.
A coincidence needs both blocks live, so its live fraction is the product of the two blocks':

```{.python include="tools/recon/corrections.py" snippet="deadtime"}
```

The rate m is every single the block recorded, whatever its energy, which is why the singles
counter counts per block outside the window too. The simulator models dead time when asked
(`--deadtime`), and the measurement compares the live fraction from the per-block singles with the
trues that the dead time actually cost:

```{.text include="measurements/ch27/corrections.txt" from="## 5." to="Trues binned"}
```

At 109 kHz per block a single is live 97.8% of the time and a coincidence 95.7%, and the estimate
from the recorded singles agrees with the two runs to 0.03%, well inside the 0.37% that the trues'
counting allows. That is the easy case, because the correction uses the same model that the
simulator applied.

The model's kind (non-paralyzable, paralyzable, or the mixture a real front end has) and its tau
come from the electronics' design and a count-rate measurement (Chapter 11); a wrong kind gives a
correction that is right at low rates and wrong at high ones. The record holds whole-run totals,
so a dynamic study, whose frames have different rates, needs per-frame singles that MiniDAQ does
not record yet (ADR 0022).

### Decay

The tracer decays during the scan, so the counts of a frame must be scaled to the activity at a
reference time, usually the start of the scan or the injection. For a frame from t0 to t0 + T after
the reference time and a decay constant lambda = ln 2 / half-life, the factor is exp(lambda t0) for
the decay before the frame, times lambda T / (1 - exp(-lambda T)) for the decay during it:

```{.python include="tools/recon/corrections.py" snippet="decay"}
```

For fluorine-18, half-life 109.77 minutes (verify: NIST and DDEP), a frame of 10 minutes starting
60 minutes after the reference gets 1.5072. Correcting to the frame's start alone gives 1.4606,
3.1% low. `expm1` keeps the digits for a frame much shorter than the half-life, where
1 - exp(-lambda T) is a difference of two numbers close to 1.

## Everything together

The last section of the measurement applies the corrections one after the other to the phantom and
shows the radial profile of the central slices after each step. A uniform cylinder corrected
correctly is flat inside the source:

```{.text include="measurements/ch27/corrections.txt" from="| Step |" to="Outside the source"}
```

The measured prompts rise by 60% from the center to the edge of the source: chords through the
center cross more water, so attenuation removes more of their pairs. Subtracting the randoms and
normalizing change little in shape, because both are nearly uniform here. Subtracting the scatter
makes the profile steeper, because scatter fills in the center most. Dividing by the attenuation
makes it flat: 1.9% rms, against 1.1% for the truth's own trues divided by the same normalization
and attenuation, whose noise is the Poisson noise of the columns. The difference is the scatter
estimate, 14% high, which leaves the center a few percent low. The truth rows are equal whether the
normalization is the measured one or the true efficiencies, so the normalization's own error does
not show at this scale; it shows as noise and patterns in an image (Chapter 28).

Two things are not in this table and no test of the software can give them: a patient whose outline
is not a cylinder, and a scatter model that is not the patient's. The tool's tests prove that each
correction computes what it claims on data whose answer is known; whether the models fit a patient
is the validation of the image chain, with phantoms and with the methods of Chapter 30.

::: box-regulated
- **The corrections tool makes part of the image.** Its output is applied to every study and nobody
  checks it line by line, so it is qualified as a tool of class T3 (TL-30), like the calibration
  procedure: its tests on known data, the comparison with `minidaq_listmode` bin for bin, and the
  measurement against the simulator's truth are its evidence. In many products the corrections are
  part of the reconstruction software, a software item of its own with its class; where the line
  between tool and product runs is a decision to record (assumption: confirm with team).
- **Corrections from the wrong inputs are a hazard.** H-12 (corrections computed from inputs that
  do not belong to the data) refines the preliminary hazard of wrong quantitative values. Its
  controls are the run record's inputs (RC-39) and the tool's refusal of a normalization with other
  settings (RC-40). Its residual is the models: outline, scatter shape, dead-time kind.
- **The run record is an interface.** Its `corrections` object is specified (MDQ-L1, version 3),
  versioned (`format: 1`) and tested on both sides: the C++ test checks that the service writes it,
  the Python test that the tool reads and checks it.
- **Each estimator's assumptions are requirements on the acquisition.** The singles estimate of the
  randoms assumes the kill-all rule and an energy window shared with the sorter; the normalization
  assumes the scan's settings are the run's. Write them down where the next person changing the
  sorter will find them: in the SRS, the ADR and the tool's docstrings.
:::

::: box-mistakes
- **A textbook estimator for your sorter.** `2 tau S_a S_b` counts randoms that your sorter's rules
  can never record. Check every estimator against a simulation of your own sorter.
- **Forgetting the 2 in 2 tau.** The other single may come first.
- **A normalization from another energy window.** Efficiencies depend on the window, the
  coincidence window and the calibration. Refuse the mismatch in the tool, not in a checklist.
- **Subtracting raw delayeds per bin.** Unbiased, and it doubles the noise of the randoms. Smooth
  them or use the singles.
- **A Gaussian for short tails.** Tail fitting needs the shape inside the object; the tails alone
  cannot give it.
- **Least squares on normalized counts.** A bin of low sensitivity holds zeros and rare huge values.
  Fit counts with a Poisson likelihood.
- **Comparing in normalized units.** S / n per bin blows up where n is small; compare estimates
  with the truth in counts.
- **Units.** mu in 1/cm with lengths in mm is a factor of 10 in the exponent.
- **Decay to the frame's start.** The activity falls during the frame too.
:::

::: box-askteam
1. Which corrections does your reconstruction apply, in which order, and which are in the system
   model rather than applied to the data?
2. How are the randoms estimated: delayed window, singles, or both? Has the estimator been checked
   against your sorter's rules at clinical count rates?
3. How is the normalization measured, how long does the scan take, how often is it repeated, and
   what makes it invalid (a new energy window, a new calibration, a replaced block)?
4. Where does the attenuation map come from, and how is a mismatch between the map and the patient
   detected?
5. Which scatter model is used, and how is its scale fitted? What happens when the tails are cut by
   the bed or the field of view?
6. What dead-time model does the front end have, measured how, and up to which count rate is the
   correction validated?
7. Which settings of the acquisition does the reconstruction read, and from where? What happens if
   one is missing?
:::

## Exercises {.unnumbered}

**Exercise 27.1 (M): Crystal efficiencies from a normalization scan.** *Goal:* find each crystal's
relative efficiency from the coincidences of a normalization scan, for a source whose projection
you know, and normalize another scan with it. *Starter:*
`exercises/ch27/e1_normalization/starter/norm.py`. *Acceptance:* `tests/test_norm.py` passes: a
centered and an off-center cylinder within 1.3 times the Poisson error rms, a second scan left with
no pattern of the crystals, and a dead crystal named and its lines 0. Then answer in `NOTES.md` how
many counts per crystal a normalization needs, why the starter failed on this small scanner, and
what a recalibration does to an old normalization. *Time:* 90 minutes.

**Exercise 27.2 (M): The randoms of every line.** *Goal:* estimate the randoms of every line from
the singles rates and from the delayed coincidences with their noise removed. *Starter:*
`exercises/ch27/e2_randoms/starter/randoms.py`. *Acceptance:* `tests/test_randoms.py` passes: the
singles estimate exact, and the variance-reduced estimate within 4.5 times the Poisson error per
crystal, with less than 0.15 times the noise of the delayeds, for fans of 48 and 16 crystals. Then
answer in `NOTES.md` what subtracting raw delayeds does to MiniDAQ's sinograms, why the singles
estimate was 31% high, and which estimate you would give the reconstruction. *Time:* 90 minutes.

**Exercise 27.3 (S): A head outline and the decay of a frame.** *Goal:* compute the attenuation
correction of an elliptical head outline, off center and turned, and the decay factor of a frame.
*Starter:* `exercises/ch27/e3_attenuation/starter/attenuation.py`. *Acceptance:*
`tests/test_attenuation.py` passes: chords of circles and of 40 random ellipses against a
measurement along the line, the factor of 200 mm of water, and decay factors that give frames of any
length the same activity. Then answer in `NOTES.md` how wrong a line is with an outline 5 mm too
large, which shortcut for the decay is good enough, and why the attenuation of a line does not
depend on where the annihilation was. *Time:* 60 minutes.

## MiniDAQ milestone: the corrections and their inputs {.unnumbered}

::: box-milestone
**Goal.** Every run record carries what the corrections need from the acquisition, and a
corrections tool computes normalization, randoms, attenuation, scatter, dead time and decay from
the list mode and the record, refuses a normalization with other settings, and is measured
against the simulator's truth. **Start:** tag `ch26`. **End:** tag `ch27`.
:::

1. Write change request CR-0013 and ADR 0022; add SRS-COR-001 to SRS-COR-003 and SRS-SIM-023 (SRS
   version 16), hazard H-12 with RC-39 and RC-40, and tool TL-30; update the MDQ-L1 specification
   (version 3) and the architecture description (version 13).
2. Add `processing/singles_counter` and its tests, count in the decode stage, and measure the cost
   with the pipeline benchmark.
3. Add `control/corrections_record` and write it into the run record at the end of every run; test
   it through the service.
4. Give `minidaq_sim` crystal efficiencies, an extended source for normalization scans and truth
   sinograms.
5. Add `tools/recon` with its tests, including the binning against `minidaq_listmode sino` bin for
   bin, the measurement `measurements/ch27/corrections.py`, and Exercises 27.1 to 27.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-COR-001 to SRS-COR-003 verified; the measurement's randoms
estimate is within 3% of the truth, the corrected profile of the phantom is flat within 2% rms,
and the tool refuses a normalization from another energy window; every starter of the chapter
fails. Tag `ch27`.

## Check yourself {.unnumbered}

1. Write the measurement model of a line of response and derive the order of the corrections from
   it.
2. Why does the singles counter count per crystal only singles in the energy window, and per block
   every single?
3. Why does the run record carry the 18,432 singles counts and the status not?
4. Derive `R = 2 tau s_a s_b`. Where does the 2 come from?
5. The singles estimate was 31% high and the delayed window 7.1% high. Explain both from the
   kill-all rule.
6. What is a component-based normalization, and why does the mean over the ring pairs of a bin
   reduce the crystals' errors?
7. How many counts does a normalization scan need for 1% per crystal on an 18,432-crystal scanner?
8. Name four settings that make a normalization invalid for a run, and say how the tool knows.
9. Why is the attenuation of a PET line independent of where the annihilation was?
10. Why did a Gaussian tail fit give 2.4 times the scatter here, and what did the model shape need
    to work?
11. Why did a least-squares scale run 22% low, and what does a Poisson likelihood scale do instead?
12. The tails hold six randoms per scatter count. What does a 2% error of the randoms do to the
    scatter estimate?
13. A non-paralyzable dead time of 200 ns and 100 kHz of singles per block: the live fraction of a
    single and of a coincidence?
14. The decay factor of a frame from 60 to 70 minutes after the reference, with fluorine-18. Why is
    the factor at the frame's start wrong?
15. Which parts of the corrections can no software test validate, and what does?

## Summary {.unnumbered}

- Prompts are `n (A L T + S) + R`. The corrections, in order: subtract the randoms, divide by the
  normalization and the live fraction, subtract the scatter, divide by the attenuation, multiply by
  the decay factor.
- MiniDAQ records what the acquisition alone knows: each crystal's singles in the energy window,
  each block's singles, the windows and the window mode, the prompts and delayeds, in the run
  record's `corrections` object. The counter's cost is not measurable on the pipeline benchmark.
- `tools/recon` (TL-30, numpy only) reads the list mode with every check, bins it exactly as the
  C++ histogrammer does, and computes each correction; the simulator's truth sinograms measure
  each one.
- Randoms from the singles must leave out the singles already paired: +31.1% without, -1.8% with.
  The delayed window was +7.1% (the kill-all bias) and much noisier per bin.
- The component-based normalization from six 5 s scans at 10 MBq: crystal efficiencies 3.4% rms,
  bins 1.4%. A normalization belongs to its energy window, coincidence window, window mode and
  calibration, and the tool refuses one that does not match.
- A Gaussian tail fit gave 2.4 times the scatter for a head's short tails; a model's shape scaled by
  Poisson likelihood gave 1.14, and the excess is the randoms in the tails. One scale per slice was
  42% noisy.
- After all corrections the phantom's profile is flat within 1.9% rms, against 1.1% for the truth's
  own noise. The models (outline, scatter shape, dead-time kind) are the residual of H-12, for the
  validation of Chapter 30.

## Further reading {.unnumbered}

- D. L. Bailey, D. W. Townsend, P. E. Valk and M. N. Maisey (editors), *Positron Emission
  Tomography: Basic Sciences*, Springer, 2005: the chapters on data corrections and quantification,
  for each correction of this chapter in more depth.
- S. R. Cherry, J. A. Sorenson and M. E. Phelps, *Physics in Nuclear Medicine*, 4th edition,
  Elsevier, 2012: the PET chapters, for the measurement model and the sources of each correction.
- M. E. Casey and E. J. Hoffman, "Quantitation in positron emission computed tomography: 7. A
  technique to reduce noise in accidental coincidence measurements and coincidence efficiency
  calibration", *Journal of Computer Assisted Tomography* 10(5), 1986: the variance reduction of
  Exercise 27.2 and the fan-sum efficiencies of Exercise 27.1.
- R. D. Badawi and P. K. Marsden, "Developments in component-based normalization for 3D PET",
  *Physics in Medicine and Biology* 44(2), 1999: the factors of a component-based normalization and
  how each is measured.
- C. C. Watson, D. Newport and M. E. Casey, "A single scatter simulation technique for scatter
  correction in 3D PET", in *Three-Dimensional Image Reconstruction in Radiology and Nuclear
  Medicine*, Kluwer, 1996: the scatter model that most tail-scaled corrections use.
- C. W. Stearns and others, "Random coincidence estimation from single event rates on the Discovery
  ST PET/CT scanner", IEEE Nuclear Science Symposium Conference Record, 2003: a singles estimate
  corrected for the singles in coincidence (verify: the authors and pages before you cite it).
- The NIST XCOM database, for the attenuation coefficients of water and tissue at 511 keV, and the
  NIST or DDEP tables of half-lives (verify: the current values).
- The documentation of open-source reconstruction software, for example STIR and CASToR, for how
  each correction enters a reconstruction (verify: what each project currently documents).
- ADR 0022, CR-0013 and the MDQ-L1 specification in the repository: the decision, the change
  record and the run record's `corrections` object.
