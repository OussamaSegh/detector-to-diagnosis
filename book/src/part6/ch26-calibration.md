# Detector calibration: energy, timing and the procedure behind them {#ch26}

::: box-why
Every number in a PET image starts as an energy code and a time stamp from one crystal, and no two
crystals report them alike. One crystal's SiPM gives 10% more charge than its neighbor's, every
SiPM's response bends at high energies as its cells run out, and every timing channel has its own
cable and electronics delay. Uncalibrated, the energy window keeps a different share of each
crystal's events and the coincidence window misses true pairs, and nothing reports an error.
Calibration is where the physicists' procedure and the DAQ software meet: a table of numbers per
crystal, made from a calibration acquisition, applied to every single, and trusted by every image
until the next one. This chapter builds all three parts: the table and its checks in the server,
the correction in the pipeline, and the procedure that makes the table, with the acceptance
criteria that decide whether it may be used. You will also see a calibration that passes every
criterion and is still wrong, which is why the criteria are a design problem of their own.
:::

**A day in the life.** On Wednesday a physicist brings you two calibration tables of the same
scanner, made a week apart, and a question: the second one was made after a detector block was
replaced, and since then the images of the daily quality-control phantom have a faint ring. The
tables look alike, 18,432 rows of numbers each. You diff them: the replaced block's gains changed,
as they should, but so did the delays of every crystal in the ring, by up to 300 ps. The
calibration log shows why. The technician could not find the cylinder phantom and used a point
source at the center instead, and the procedure, which then checked only photopeak counts and the
timing residual, accepted the result: the residual was even smaller than usual. By Friday the
procedure refuses a source that pairs each crystal with too few others, the server refuses a table
that is damaged, made for another scanner or expired, and the run record of every acquisition says
which table it used, so the physicist can list the runs that the bad table touched.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what a front-end board's energy code and time stamp mean for an uncalibrated crystal:
   gain, saturation of the SiPM and channel delay, and what each does to the energy window, the
   coincidence window and the images.
2. Design a calibration table: its model, its limits, its file format and its integrity check, and
   how a server checks that a table belongs to the scanner and is still valid.
3. Apply a per-crystal correction in a streaming pipeline without breaking its time order, and
   prove that it does not.
4. Fit a photopeak as a Gaussian on a background, derive an energy curve from it, and solve channel
   delays from coincident pairs by least squares on a graph.
5. Write acceptance criteria for a calibration procedure, including criteria that detect the wrong
   input, and test that the procedure refuses what it should.
6. Place a calibration procedure in a regulated life cycle: tool qualification, risk controls,
   traceability from a run to its table, and the checks during a run.

## Prerequisites and estimated time {.unnumbered}

Chapter 8 (PET physics: photopeak, Compton scatter, time of flight), Chapter 10 (the coincidence
sorter), Chapter 12 (the list-mode file and its run record), Chapter 15 (risk management) and
Chapter 22 (the SiPM bias and its temperature dependence). You need Python 3 with numpy for the
procedure and the exercises. Reading: about 3 hours. Exercises: 4 to 5 hours. Milestone: 6 hours.
If time is short, do Exercises 26.1 and 26.3.

## What an uncalibrated detector reports

### Three ways two crystals differ

The front-end board of Chapter 9 sends, for each single, a crystal number, an 11-bit energy code
and a time stamp in units of 5 ps. MiniDAQ took the energy as the code times 0.5 keV and the time
as the board sent it, which is right only for an ideal detector. A real one differs from crystal to
crystal in three ways.

- **Gain.** The light a crystal makes per keV, the fraction that reaches its SiPM, the SiPM's
  photon detection efficiency and its overvoltage (Chapter 22) all vary. The charge per keV, and so
  the code, varies by about 10% between crystals of one scanner (assumption: confirm with team for
  your detectors).
- **Saturation.** A SiPM has a fixed number of cells, and a cell that has fired cannot fire again
  within the pulse. As more photons arrive, more of them hit cells that already fired, and the
  response bends: for a SiPM of N cells and n photons detected, the cells fired are about
  N (1 - exp(-n / N)). In energy terms the response is S(E) = E_sat (1 - exp(-E / E_sat)), with
  E_sat a property of the sensor and the crystal, measured once on the bench. With E_sat = 1500
  keV, a 511 keV photon gives the response of a 433 keV one in a linear detector, 15% low.
- **Delay.** The time from the photon's interaction to the time stamp differs per channel: the
  SiPM, the trace on the board, the ASIC's input stage and its time-to-digital converter. Hundreds
  of picoseconds between channels are normal before calibration, and the coincidence time
  resolution the scanner is specified for is a few hundred picoseconds (Chapter 8).

`minidaq_sim` simulates all three since this chapter. With `--gain-spread 0.1 --saturation 1500
--time-skew 500` every crystal gets its own gain (10% rms, kept within 0.6 to 1.6), the SiPM
saturates with an E_sat of 1500 keV, and every channel gets its own delay (500 ps rms, kept within
4 ns). `--crystal-truth FILE.csv` writes what a calibration should find: each crystal's gain, its
delay and the saturation energy, which no real detector would tell you.

Figure [](#fig-ch26-saturation) draws the curve, and the next section comes back to its inverse.

```{.figure #fig-ch26-saturation src="book/figures/plots/ch26/saturation.py" caption="The SiPM's saturation with E_sat = 1500 keV (left), and how far a quadratic fitted to its inverse is from the exact inverse (right). Fitted on 200 to 700 keV it stays within 0.44% there; fitted down to 100 keV it is 1.5% off at the low end." alt="Left: response against deposited energy, a straight dashed line for a linear detector and a curve bending below it, with 511 keV reading as 433, 15% low. Right: the error of the quadratic in percent against energy, a solid curve for a fit on 200 to 700 keV within about plus or minus 0.4%, and a dashed curve for a fit on 100 to 700 keV reaching 1.5% at 100 keV; the energy window is shaded." width="100%"}
```

### What it does to the data

On the simulated detector, the summed energy spectrum of all crystals has its photopeak at 435 keV
instead of 511, and 23.0% FWHM wide instead of the 12.0% of a calibrated detector
(`measurements/ch26/calibration.txt`). The energy window of 435 to 585 keV that MiniDAQ's sorter
uses (Chapter 10) then cuts through the middle of most crystals' photopeaks, and keeps a share of
each crystal's events that depends on that crystal's gain: a crystal with a high gain keeps all of
its photopeak, one with a low gain keeps half. The image gets the pattern of the gains, which a
normalization (Chapter 27) can partly correct, and the scatter fraction becomes position-dependent,
which it cannot.

Figure [](#fig-ch26-spectra) shows the effect crystal by crystal and summed.

```{.figure #fig-ch26-spectra src="book/figures/plots/ch26/spectra.py" caption="Energy spectra from the simulator's model, drawn with a fixed seed. Each crystal's photopeak sits where its gain puts it, and the energy window keeps a different share of each; the summed spectrum is wide and low until the calibration puts every photopeak at 511 keV." alt="Left: four crystals' spectra as reported, with gains 0.85, 0.95, 1.08 and 1.20, photopeaks between about 370 and 520 keV, against the shaded window from 435 to 585 keV. Right: the summed spectrum of 2,000 crystals, uncalibrated with a broad peak at 435 keV and 23% FWHM, and calibrated with a narrow peak at 511 keV and 12% FWHM." width="100%"}
```

The delays do the same to time. Two crystals whose delays differ by 1 ns see their true
coincidences 1 ns off center in the coincidence window; with a narrow window some of them fall
outside, and the time-of-flight information that localizes each annihilation along its line of
response (Chapter 8) is wrong by 15 cm for every nanosecond. The data stream itself has a problem
too, which the next section handles: a time correction reorders the singles.

## The calibration table

### The model

MiniDAQ's table holds four numbers per crystal:

```{.cpp include="minidaq/include/minidaq/processing/calibration.hpp" snippet="crystal"}
```

The energy is a quadratic in the board's code c, E = a + b c + q c^2; the time is the reported
time minus the offset. The identity table (a = 0, b = 0.5 keV, q = 0, offset 0) changes nothing,
and is what a server without a calibration uses. The table also records which scanner it was made
for, its id and version, when it was made and until when it is valid, the detector temperature
during the calibration acquisition, and the procedure that made it.

Why a quadratic and not a lookup table of 2,048 energies per crystal? The lookup table would be
exact and 150 MB; three coefficients per crystal fit in 300 kB, are easy to check against the
limits of a working detector, and make a wrong curve visible. The price is accuracy: the exact
inverse of the saturation, E = -E_sat ln(1 - S / E_sat), is not a quadratic. Fitted over 200 to 700
keV, the range of the energy window and the scatter just below it, a quadratic is within 0.44% of
it for every crystal of the simulated detector; fitted down to 100 keV it would be 1.5% off
somewhere. A calibration's model is a design decision with a range of validity, and the range
belongs in the documentation (ADR 0021).

Applying the table to a single is three multiplications, two additions and a subtraction:

```{.cpp include="minidaq/include/minidaq/processing/calibration.hpp" snippet="apply"}
```

### The limits of a working detector

A table is a file, and a file can be wrong in ways its reader must refuse. `CalibrationTable::make`
checks every entry against limits that no working detector exceeds, and refuses the whole table if
one entry fails:

```{.cpp include="minidaq/src/processing/calibration.cpp" snippet="check"}
```

The limits are deliberately loose. They are not the procedure's acceptance criteria, which are
tighter and come later in the chapter; they bound what the server will ever apply, whoever made the
table. One of them was wrong in the first version, and the end-to-end measurement found it: the
curvature was bounded at 40% of the linear term at the top code in both directions. A saturating
SiPM bends the curve up, and for a crystal of gain 0.6 behind a SiPM with an E_sat of 1500 keV the
quadratic term at code 2,047 is 1.15 times the linear one. The first table the procedure wrote was
refused by the server for every one of its 18,432 crystals. The limit is now 0.4 down and 1.5 up,
the procedure checks the server's limits itself before it writes, and a test of each side checks
that both have the same limits.

### The file and its integrity

The table is a JSON document of about 1 MB, specified in `docs/formats/calibration.md`: the
identification, the number of crystals, three arrays of energy coefficients, one array of offsets,
and a CRC-32. The reader is strict in the way Chapter 17 asked of every input: every key is
required, an unknown key is an error, every number must fit its type (a coefficient beyond the
range of a float or an offset beyond 32 bits is refused, not rounded), and the first five bad
values of each array are named with their index.

Figure [](#fig-ch26-table) puts the parts of the file together.

```{.figure #fig-ch26-table src="book/figures/tikz/ch26/table.tex" caption="The calibration table: a header that says what the table is for and until when, four numbers per crystal (the entries shown are examples), and what makes the server refuse the whole table." alt="Left, the header with id CAL-0002 version 2, scanner MDQ-REF-0001, made 2026-11-03 and valid until 2027-02-01, procedure CP-026, 25 degrees, and the CRC-32; below it a table with columns crystal, a, b, q and offset in ps for crystals 0, 1 and 18431, and the two formulas. Right, five reasons the server refuses a table: a CRC that does not match, another scanner, expired, an entry outside the limits, a missing or unknown key." width="85%"}
```

The CRC covers the coefficients as the reader converted them: 16 bytes per crystal, three floats
and an integer, little-endian:

```{.cpp include="minidaq/include/minidaq/processing/calibration.hpp" snippet="canonical"}
```

Computing it after the conversion matters. A writer and a reader that rounded a decimal number to a
float differently would produce different coefficients from the same file, and a CRC over the text
would not notice. A CRC over the converted values does, and the procedure writes each coefficient as
the decimal number that is exactly its float value, so that the conversion is exact in every
reader. A CRC is not a signature: it detects damage and editing by hand, and anyone who can write
the file can also write a matching CRC. The table's authenticity rests on the permissions of the
configuration directory, as the configuration's own does. ADR 0021 records why a signature was not
chosen (it would need a signing key at every site that calibrates), and why SHA-256 was not either:
the configuration layer does not use OpenSSL (Chapter 14, layers).

### Which table, for which scanner, until when

The acquisition configuration names the table and the scanner it must belong to (schema 1.4):

```json
"calibration": { "file": "/etc/minidaq/calibration/CAL-0002.json",
                 "scanner_serial": "MDQ-REF-0001", "drift_tolerance_percent": 2.0 }
```

The service reads and checks the table when the acquisition is configured, not when a run starts,
so that an operator learns about a bad table before the patient is on the bed:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="configure-calibration"}
```

A table copied from another scanner is the most likely wrong table there is: two scanners of one
model have files that look alike, and a service engineer with a USB stick has both. The serial
check makes it a configuration error. The expiry makes a calibration that nobody renewed a
configuration error too, on the day it expires and not when someone notices the images. The
measurement configured `minidaq_server` with the table the procedure wrote, once with the right
serial and once with another one:

```{.text include="measurements/ch26/calibration.txt" from="## 4." to="## 5."}
```

The status (control API 2.4) names the table in use, and so does the run record and the metadata of
every list-mode file (SRS-CAL-005). That is the traceability of the day in the life: given a table
found wrong, the runs it touched are a search over the run records.

## Applying the table in the pipeline

### The decode stage

The correction belongs where the singles are decoded, before anything uses their energy or their
time. MiniDAQ's decode stage applies the table to each batch right after decoding it, and only when
the table is not the identity:

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="decode"}
```

Its cost was not measurable: the pipeline benchmark of Chapter 5 (BM_Pipeline/4096/64) ran at about
30 M singles/s with and without a table. A few multiplications per single are nothing next to the
memory traffic of moving it between stages.

### A time correction reorders the singles

The sort stage orders the singles of each batch by time, and the sorter downstream relies on the
stream being ordered across batches too (Chapter 10). The board delivers its singles in the order of
its time stamps. After the correction subtracts each crystal's own offset, that order is gone: a
single reported at 1,000 ps by a crystal with an offset of -300 ps is corrected to 1,300 ps, and a
single reported at 1,100 ps by a crystal with an offset of +400 ps is corrected to 700 ps. The
second single arrives later and belongs earlier. If the first was already in an earlier batch that
the sort stage passed on, the second one is late, and the sorter counts it and loses its
coincidences.

The bound is the spread of the offsets: a single can come out at most (largest offset minus smallest
offset) earlier than one already seen. The sort stage holds back the singles that are within that
spread of the newest one, and sends them with the next batch:

Figure [](#fig-ch26-reorder) shows the two singles of the example and the hold-back.

```{.figure #fig-ch26-reorder src="book/figures/tikz/ch26/reorder.tex" caption="A time correction reorders the singles. A arrives first and is corrected to later; B arrives later and is corrected to earlier. The sort stage holds back every single within the offsets' spread of the newest corrected time." alt="Two time axes from 600 to 1400 ps. On the reported axis, A at 1000 ps with offset minus 300 and B at 1100 ps with offset plus 400. Arrows take A to 1300 and B to 700 on the corrected axis. Below, a bar shows the singles older than the newest corrected time minus the spread of the offsets as free to go, and those within the spread as held for the next batch." width="90%"}
```

```{.cpp include="minidaq/src/pipeline/acquisition_pipeline.cpp" snippet="sort-hold"}
```

The comment at the top is the proof, and it is worth reading twice: every single already seen has a
corrected time of at most the newest reported time minus the smallest offset; every later one has
at least the newest reported time minus the largest offset; so a held single older than the newest
corrected time minus the spread can no longer be preceded, and may go. A pipeline test,
`CalibratesEverySingleAndTheCorrectionMakesNoneLate`, runs a table whose offsets span 600 ps
through the pipeline: without the hold-back, 47 of its singles came out late; with it, none. For the
simulated detector the spread is 4,077 ps, the `time_spread_ps` of the table in the status. Without
a table the hold-back is zero, and the stage is what it was.

## Making the table: the procedure

### The calibration acquisition

The procedure, `tools/calib`, is a Python package with numpy and nothing else (TL-29). It takes the
singles of one calibration acquisition, in the readout's word format:

```text
python3 -m tools.calib SINGLES.words --out CAL-0002.json --report report.json \
    --id CAL-0002 --version 2 --serial MDQ-REF-0001 --e-sat 1500
```

and writes the table, or refuses to and says why. The acquisition is a uniform cylinder of activity
centered in the ring, without anything around it to scatter in. The simulation used `minidaq_sim
--source cylinder --phantom 0` at 20 MBq for 3 s: 29 million singles, of which every crystal had at
least 809 in its photopeak. On a real scanner the source is a few MBq and the acquisition takes
minutes; the number of singles per crystal is what matters.

Why a cylinder? The energy calibration needs any source of 511 keV photons that reaches every
crystal. The timing calibration needs more, as the section on delays shows. The procedure has four
steps: each crystal's photopeak, its energy curve, the delays, and the acceptance criteria.

Figure [](#fig-ch26-procedure) is the order of the steps.

```{.figure #fig-ch26-procedure src="book/figures/tikz/ch26/procedure.tex" caption="The calibration procedure. The energy comes first, because the pairs for the delays are chosen in the calibrated window; the acceptance criteria decide whether a table is written at all." alt="Flow: acquisition of a centred cylinder at 20 MBq for 3 s, photopeak per crystal, energy curve, isolated pairs in the calibrated window, delays by least squares with outliers trimmed, acceptance criteria per crystal. If all pass, a table with id, version and CRC is written; if one fails, no table, and a report names each crystal. A note lists the criteria: counts, fit, curve error, gain limits, pairs and at least 40 partners." width="65%"}
```

### Photopeaks

Each crystal's spectrum is a histogram of its codes, 4 codes per bin. Its photopeak is a Gaussian on
a background: below it the Compton continuum and any scatter, above it pile-up. The procedure fits
all 18,432 crystals at once, with array operations:

```{.python include="tools/calib/energy.py" snippet="peak"}
```

Three choices in it are worth knowing because each was wrong once, in Exercise 26.1 or in the first
version of this code.

- **The background bands.** The background is a straight line through two bands of the spectrum on
  either side of the peak. Bands just outside the fitted window (2 to 2.5 sigma) still hold the
  peak's own tails, 13% of its height at 2 sigma, and made sigma 11.5% too small. At 3 to 3.5 sigma
  the Gaussian is down to 1%.
- **Guo's weights.** A Gaussian is a parabola in the logarithm, so a linear least-squares fit of a
  parabola to the logarithm of the counts gives its center and width without starting values or
  iteration. Unweighted, it gives the noisy logarithms of the small counts in the tails as much say
  as the peak; Guo's weights, the counts squared, give each point the say its counts deserve.
- **Half a bin.** Bin k holds codes 4k to 4k + 3, so its center is code 4k + 1.5. Forgetting that
  is a bias of 0.15% in every gain, the size of the whole calibration's error.

The gain follows from the photopeak's code: the code a linear detector of gain 1 would give for 511
keV is S(511) / 0.5 keV, and the crystal's gain is its photopeak's code divided by that.

### The energy curve

With each crystal's gain g, its code for an energy E is c = g S(E) / 0.5 keV, and the curve the
server needs is the inverse. The procedure fits the quadratic to the exact inverse over 200 to 700
keV, batched over all crystals:

```{.python include="tools/calib/energy.py" snippet="curve"}
```

`worst` is how far the quadratic is from the exact inverse anywhere in the range, which an
acceptance criterion bounds at 1%; on the simulated detector it was at most 0.44%. Note what the fit
assumes: that E_sat is the sensor's, given on the command line from a bench measurement. A wrong
E_sat gives a curve that fits the wrong inverse perfectly. No criterion of this procedure can see
that, and the section on what the criteria cannot see comes back to it.

### Delays by least squares

A pair of singles from one annihilation, seen by crystals i and j, has a time difference t_i - t_j =
(d_i - d_j) + (the difference of the two photons' flight times) + noise. For a uniform cylinder
centered in the ring, the activity along each line between two crystals is symmetric about the
line's midpoint, so the flight times' difference is zero on average, and the delays are the
least-squares solution of t_i - t_j = d_i - d_j over all pairs, up to a constant that no coincidence
can see.

The pairs come from the calibrated singles: two singles in the energy window closer than 4 ns, with
no third one within 4 ns of either:

```{.python include="tools/calib/timing.py" snippet="pairs"}
```

The least-squares problem has 18,432 unknowns and millions of equations. Its normal equations are
L d = r, where L is the Laplacian of the graph whose nodes are the crystals and whose edges are the
pairs: L_ii is the number of pairs crystal i is in, L_ij is minus the number of pairs of i with j.
L is sparse, symmetric and positive semi-definite, which is exactly what conjugate gradients solve,
and the product L x needs no matrix at all, only two `bincount`s over the pairs:

```{.python include="tools/calib/timing.py" snippet="solve"}
```

On 2.7 million pairs the solver took 54 iterations and a few seconds. Some pairs are random
coincidences, two photons of different annihilations whose time difference is anything within the
window; they pull every delay toward zero. The procedure solves, sets aside the pairs whose residual
is beyond four robust standard deviations, and solves again until the set no longer changes:

```{.python include="tools/calib/timing.py" snippet="trim"}
```

It set aside 177,407 of the 2,730,558 pairs, 6.5%. The residual of the rest, 326 ps rms, is the
coincidence time resolution (300 ps FWHM, 127 ps rms, in the simulation) and the cylinder's own
spread of flight times (an annihilation 80 mm from a line's midpoint arrives 530 ps earlier at one
end than at the other), together.

### Results against the truth

The simulator's truth file makes the one comparison a real calibration never gets:

| Quantity | Result |
|---|---|
| Gain error | mean +0.026%, rms 0.18%, worst 0.74% |
| Each crystal's true photopeak through its curve | mean 511.2 keV, rms 1.1 keV, worst 4.3 keV from 511 |
| Delay error (common constant removed) | rms 20.9 ps, worst 90 ps, for delays of 496 ps rms |
| Delay error in the two rings at each end | rms 22.8 ps, mean +9.8 ps |
| Summed photopeak | 435 keV and 23.0% FWHM before, 511 keV and 12.0% after |
| Time | 95 s to simulate, 29 s to calibrate |

: The calibration of the simulated detector (measurements/ch26/calibration.txt, section 1). Gains of 10% rms, E_sat 1500 keV, delays of 500 ps rms, a cylinder at 20 MBq for 3 s.

The end rings are slightly worse and slightly biased: the cylinder is 100 mm long in a ring 118 mm
long, so the oblique lines that reach the end rings see the cylinder's end asymmetrically, and their
mean flight-time difference is not quite zero. The bias of 10 ps is small next to the coincidence
time resolution; a longer cylinder would remove it.

## Acceptance criteria

### What the procedure checks

A calibration procedure that always writes a table is a tool that makes product data without a
check. MiniDAQ's writes a table only when every crystal passes every criterion:

```{.python include="tools/calib/__main__.py" snippet="criteria"}
```

Each criterion bounds what one step can get wrong, and each comes with its reason: the counts bound
the photopeak's statistical error, the width and gain bounds catch a fit that found something other
than the photopeak, the curve error bounds the model, the pairs bound each delay's statistical
error, the residual bounds what the delays did not explain. The values are this book's (assumption:
confirm with team, against your scanner's specification). Then the server's own limits, so that the
procedure never writes a table the server would refuse:

```{.python include="tools/calib/table.py" snippet="limits"}
```

When a criterion fails, the procedure names every failing crystal and why, writes no table, and
exits with status 1. A 0.5 s acquisition, a sixth of the needed singles, gave:

```{.text include="measurements/ch26/calibration.txt" from="## 3." to="## 4."}
```

### The calibration that passed and was wrong

The criteria above, without the one on partners, are what the day in the life's procedure had. The
measurement repeated that day: the same detector, a point source at the center instead of the
cylinder, the same 3 s.

```{.text include="measurements/ch26/calibration.txt" from="## 2." to="## 3."}
```

Without the partners criterion, every crystal passed: enough counts, good fits, and a timing
residual of 129 ps, much smaller than the cylinder's 326 ps, because a point at the center gives
every pair the same flight time. The delays were 130 ps rms wrong. The reason is the graph. A point
source at the center pairs each crystal with the few crystals opposite it and with no others: the
graph of pairs falls into small groups, joined to each other only by the few pairs that the photons'
non-collinearity and the depth of interaction add. Each group's delays are well determined relative
to each other and badly relative to every other group's; the solver needed 740 iterations instead of
54, the sign of a nearly disconnected graph, and the residual cannot see the error, because a
constant per group explains the data equally well. The cylinder pairs each crystal with a fan of
crystals across the ring, and the groups cannot form.

Figure [](#fig-ch26-graph) draws the two graphs.

```{.figure #fig-ch26-graph src="book/figures/tikz/ch26/graph.tex" caption="The graph of pairs for three crystals of a 24-crystal ring. A centred cylinder gives each crystal a fan of partners across the ring, which ties every delay to every other; a point source at the centre gives each crystal only the crystals opposite, and the graph falls into groups." alt="Two rings of 24 crystals. Left, uniform cylinder: three crystals each joined by lines to nine crystals across the ring, forming a dense web. Right, point source: the same three crystals each joined only to the three crystals directly opposite. Notes give the measured numbers: least partners 178 and delays right to 21 ps for the cylinder; at most 13 partners, 740 iterations and delays 130 ps wrong for the point source." width="70%"}
```

The criterion that catches it counts each crystal's distinct partners: at least 40. The cylinder
gave at least 178, the point source at most 13. It is a criterion on the input, not on the result,
and that is the general lesson: a fit's own quality measures say how well the model explains the
data, not whether the data could determine the model. Exercise 26.3 makes you write the connectivity
check itself.

### What the criteria cannot see

Some inputs make a table that passes everything and is wrong:

- **E_sat.** The saturation energy is given on the command line. A wrong one gives curves that put
  each photopeak at 511 keV and every other energy off: the scatter below the photopeak, and so the
  scatter correction of Chapter 27, comes out wrong.
- **The source's position.** A cylinder 20 mm off center gives the lines that pass near the offset a
  mean flight-time difference of up to 133 ps, which the solution absorbs into the delays as a
  pattern around the ring (Exercise 26.3). The residual is no larger.
- **A detector that changed during the acquisition**, warming up for example, gives tables that fit
  its average.

These are why the hazard of a wrong calibration (H-11) keeps a residual risk: the daily quality
control with a phantom is the control for them (assumption: confirm with team). They are also why a
calibration procedure belongs under the same change control as the software: the source, its holder
and its position are part of the procedure, and a procedure document with a version is what the
table's `procedure` field names.

## Watching the calibration during a run

A table is right when it is made and drifts afterwards: a block's temperature changes (Chapter 22
compensates the bias, not perfectly), a board is replaced, a SiPM ages. The server checks the table
against the data it calibrates, every run. The decode stage records each calibrated single between
430 and 590 keV in a per-block counter:

```{.cpp include="minidaq/include/minidaq/processing/calibration.hpp" snippet="monitor"}
```

and the status reports each block's count and mean energy, and the blocks whose mean is further from
511 keV than the tolerance, once they have 1,000 singles to say so:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="calibration-status"}
```

The mean of a window is not the photopeak's center: the scatter under the photopeak pulls it down.
With a 90 mm water phantom around the cylinder, a patient's worth of scatter, the mean was 506.5
keV, 0.9% below 511 (section 5 of the measurement). A tolerance of 2% leaves about 1% for a real
drift before a patient scan is flagged, and a flagged block is a reason to look, not a fault: the
run goes on, and the operator and the physicist decide (assumption: confirm with team how a drift
alarm is handled). A drift that the monitor names in the daily quality control, with a known
phantom, is a reason to recalibrate.

::: box-regulated
- **The procedure is a tool that makes part of the product.** IEC 62304 expects you to plan the
  tools that the development uses; ISO 13485 asks you to validate software used in production and
  service when its output is not fully verified afterwards. A calibration table is product data
  that nobody checks crystal by crystal, so the procedure is qualified as a tool of class T3
  (TL-29): its tests on a synthetic detector, the measurement against the simulator's truth, and the
  server's own checks are its evidence (`docs/regulatory/verification/tools.md`).
- **A wrong calibration is a hazard.** H-11 refines the preliminary hazard of data recorded with
  wrong settings; its controls are the server's refusal of a damaged, foreign or expired table
  (RC-35), the procedure's acceptance criteria (RC-36), the photopeak monitor (RC-37), and the run's
  record of its table (RC-38), which makes a bad table's consequences traceable.
- **The table is a configuration item.** Its id, version, scanner serial and CRC identify it as a
  SOUP item's version identifies the SOUP. A site's tables are records of the device's servicing;
  who may make them, with which procedure version and which source, belongs in the service
  documentation (assumption: confirm with team).
- **The acceptance criteria are requirements.** SRS-CAL-007 states them, and tests show that the
  procedure refuses each kind of bad input. Changing a criterion is a change to a requirement, with
  a change request.
:::

::: box-mistakes
- **Trusting a fit's own quality measure to validate its input.** The point source's residual was
  better than the cylinder's. Check that the data can determine the answer: counts, partners,
  connectivity.
- **A curve model without a range.** A quadratic is good over the range it was fitted on; say which
  range, and check it there.
- **Correcting times without thinking about order.** Any per-channel time correction in a streaming
  pipeline can reorder its output. Bound the reordering and hold back by the bound.
- **A CRC over the text.** Two readers that round differently get different coefficients from one
  file. Seal the values as the reader converts them.
- **Checking the table only in the tool.** The server must check what it applies, whoever made it,
  with limits of its own; and the tool must check the server's limits, or the first real table is
  refused in the field.
- **Calibrating with the wrong source.** Write the source, its holder and its position into the
  procedure, and add a criterion that notices when it was not followed.
- **A run that does not say which table it used.** Without it, a table found wrong cannot be traced
  to the scans it affected.
:::

::: box-askteam
1. Which calibrations does the scanner have (energy, timing, crystal identification, normalization),
   who makes each one, with which source, and how often?
2. Where are the calibration tables applied: on the boards, in the acquisition software, or in the
   reconstruction? Who owns each step?
3. What are the acceptance criteria of each calibration procedure, and which input mistakes would
   pass them?
4. How does an acquisition know which tables it used, and how would you find every scan made with a
   table that turned out to be wrong?
5. What happens when a table expires, and what happens when a block is replaced?
6. How is the drift of a calibration watched between calibrations, and what does an alarm lead to?
7. Is the calibration procedure validated as a production or service tool, and where is the record?
:::

## Exercises {.unnumbered}

**Exercise 26.1 (M): Find a crystal's photopeak.** *Goal:* fit the 511 keV photopeak of one
crystal's spectrum as a Gaussian on a straight background, and turn its center into the crystal's
gain. *Starter:* `exercises/ch26/e1_photopeak/starter/photopeak.py`. *Acceptance:*
`tests/test_photopeak.py` passes: bin positions, a clean peak within 0.1% in center and 3% in sigma,
40 spectra with patient scatter unbiased to 0.2%, and the gains of 30 crystals within 0.3% rms. Then
answer in `NOTES.md` what Guo's weights do at 300 and 3,000 counts, where the background bands
belong, and how wide a summed uncalibrated spectrum should be. *Time:* 75 minutes.

**Exercise 26.2 (M): A flood map and its crystal lookup table.** *Goal:* find the 256 crystals of a
16 by 16 block in a flood with compressed edges and bent rows, order them, and build the lookup
table that names the crystal of every pixel. *Starter:*
`exercises/ch26/e2_flood_map/starter/flood.py`. *Acceptance:* `tests/test_flood.py` passes: one peak
per crystal within 1.5 pixels, the grid in the crystals' order, more than 98% of the events
identified, and a harder block. Then answer in `NOTES.md` which crystals are hardest, where
nearest-peak boundaries go wrong, and what a board's recalibration can check automatically. *Time:*
90 minutes.

**Exercise 26.3 (H): Channel delays by least squares.** *Goal:* solve the delays of a four-ring
scanner from its coincident pairs by conjugate gradients without a matrix, refuse pairs that do not
connect every crystal, and set random coincidences aside. *Starter:*
`exercises/ch26/e3_time_offsets/starter/offsets.py`. *Acceptance:* `tests/test_offsets.py` passes:
the parts of small graphs and of a point source's pairs, the delays of a cylinder within 15 ps rms,
exact delays from exact differences, and 15% randoms set aside. Then answer in `NOTES.md` why a mean
is not a solution, what decides the number of iterations, and what a cylinder off center does.
*Time:* 2 hours.

## MiniDAQ milestone: a calibrated detector {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ applies a per-crystal energy and timing calibration to every single without
breaking the time order, refuses tables that are damaged, foreign or expired, names the table in
every run, watches the photopeak of every block during a run, and comes with a calibration procedure
whose acceptance criteria refuse bad acquisitions, including the wrong source. **Start:** tag
`ch25`. **End:** tag `ch26`.
:::

1. Write change request CR-0012 and ADR 0021; add SRS-CAL-001 to SRS-CAL-007 and SRS-SIM-022 (SRS
   version 15), hazard H-11 with RC-35 to RC-38, the calibration table's format specification, and
   tool TL-29; update the architecture description (version 12).
2. Add `processing/calibration` (the table, its limits, its CRC, the photopeak monitor) and its
   tests.
3. Apply the table in the pipeline's decode stage, add the hold-back to the sort stage, and test
   that no single is made late.
4. Add `config/calibration_file`, configuration schema 1.4 and the service's checks (serial,
   expiry), the status field `calibration` (control API 2.4) and the table in the run record and
   the list-mode metadata.
5. Give `minidaq_sim` an uncalibrated detector and its truth file.
6. Add `tools/calib` with its tests, the measurement `measurements/ch26/calibration.py`, and
   Exercises 26.1 to 26.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-CAL-001 to SRS-CAL-007 verified; the measurement's table is
loaded by `minidaq_server`, its gains are within 0.3% rms and its delays within 25 ps rms of the
truth, and the point source is refused; every starter of the chapter fails. Tag `ch26`.

## Check yourself {.unnumbered}

1. Name three ways two crystals of one scanner report the same photon differently, and what each
   does to the data if it is not corrected.
2. A SiPM with E_sat = 1500 keV: what response does a 511 keV photon give, and why does the
   calibrated curve bend up rather than down?
3. Why does MiniDAQ store a quadratic per crystal and not a lookup table, and what does that choice
   cost?
4. Why is the CRC computed over the converted values and not over the file's text? What does it not
   protect against?
5. Why does the service check the table's scanner serial and expiry at configuration and not at the
   start of a run?
6. A table's offsets range from -1,800 to +2,277 ps. How far back may a single's corrected time be
   from the newest one the sort stage has seen, and what does the stage do about it?
7. In the photopeak fit, what goes wrong with background bands just outside the window, and what
   goes wrong with an unweighted fit to the logarithm?
8. What is L in L d = r, and why can conjugate gradients solve it without building L?
9. Why do random coincidences pull every delay toward zero, and how does the procedure set them
   aside?
10. The point source gave a smaller residual than the cylinder and delays six times worse. Explain
    both, and name the criterion that catches it.
11. Name two inputs that make a table pass every criterion and still be wrong, and the control that
    catches each.
12. With a water phantom the photopeak monitor reads 506 keV for a correct table. What does that
    mean for the drift tolerance?
13. Why is the calibration procedure a tool of class T3, and what is its evidence?

## Summary {.unnumbered}

- An uncalibrated crystal's energy code depends on its gain and its SiPM's saturation, and its time
  on its channel's delay. On the simulated detector (10% gains, E_sat 1500 keV, 500 ps delays) the
  summed photopeak sat at 435 keV and was 23.0% FWHM wide; calibrated, 511 keV and 12.0%.
- MiniDAQ's table holds a quadratic energy curve and a delay per crystal, a scanner serial, an id,
  a version, a creation and an expiry time and a procedure, sealed by a CRC-32 over the converted
  coefficients. The server refuses a table outside the limits of a working detector, damaged,
  foreign or expired, at configuration.
- The decode stage applies the table at no measurable cost; the sort stage holds back the spread of
  the offsets, so the time correction makes no single late (47 late without it in the test, none
  with it).
- The procedure `tools/calib` fits each crystal's photopeak (Guo's weighted log-parabola on a linear
  background), fits the curve over 200 to 700 keV, and solves the delays by conjugate gradients on
  the Laplacian of the pair graph with outliers set aside. On the simulated detector: gains 0.18%
  rms, delays 20.9 ps rms from the truth, in 29 s.
- The acceptance criteria refuse too few counts, bad fits, implausible gains, a poor curve, too few
  pairs, too few distinct partners, a large residual and anything the server would refuse, and name
  every failing crystal. The partners criterion catches a point source, whose delays were 130 ps
  rms wrong while its residual looked better than the cylinder's.
- Some wrong inputs pass every criterion (E_sat, the source's position); the daily quality control
  stays a control for them. The photopeak monitor watches each block during every run; scatter puts
  its baseline about 1% below 511 keV.
- The procedure is a T3 tool with its qualification, a wrong calibration is hazard H-11 with four
  controls, and every run names its table.

## Further reading {.unnumbered}

- S. R. Cherry, J. A. Sorenson and M. E. Phelps, *Physics in Nuclear Medicine*, 4th edition,
  Elsevier Saunders, 2012: the chapters on scintillation detectors and PET instrumentation, for
  energy resolution, gain and timing.
- H. Guo, "A Simple Algorithm for Fitting a Gaussian Function", *IEEE Signal Processing Magazine*
  28(5), 2011: the weighted log-parabola fit of the photopeaks, and its iterative form for noisy
  data.
- J. R. Shewchuk, *An Introduction to the Conjugate Gradient Method Without the Agonizing Pain*,
  Carnegie Mellon University, 1994: the method that solves the delays, and why its speed depends on
  the condition number.
- M. Fiedler, "Algebraic connectivity of graphs", *Czechoslovak Mathematical Journal* 23(2), 1973:
  the eigenvalue of the Laplacian that says how nearly a graph falls apart, which is what the point
  source did.
- D. R. Schaart, "Physics and technology of time-of-flight PET detectors", *Physics in Medicine and
  Biology* 66(9), 2021: what sets a detector's timing and why its calibration matters (verify: the
  volume and issue before you cite it).
- The documentation of open-source PET calibration and reconstruction software, for example the
  calibration procedures of PETsys's TOFPET2 evaluation kit and the normalization and timing
  calibration in STIR and CASToR (verify: what each project currently documents).
- `docs/formats/calibration.md`, ADR 0021 and CR-0012 in the repository: the format, the decision
  and the change record of this chapter.
