# PET physics for software engineers {#ch08}

::: box-why
A coincidence sorter is a filter with physical assumptions built in: that two photons
from one decay arrive within a nanosecond or two, that they carry about 511 keV each,
that they land on opposite sides of the ring. A calibration is a correction for what the
crystals and photodetectors do to those photons. A DAQ engineer who does not know where
these assumptions come from cannot tell a software bug from a physics effect. A sorter
that "loses" 6% of its trues at high activity could be a race condition or the expected
loss to multiples, and a 4 ns window could be generous or too tight. This chapter gives
you the physics a DAQ lead needs, and no more. It also gives MiniDAQ a detector
simulator that knows the truth about every single it produces, so that every later
chapter can test its algorithms against what really happened.
:::

**A day in the life.** It is a Tuesday morning. The physicist who owns image quality stops
by: after a firmware update the scatter fraction measured with the brain phantom went
from 28% to 33%, and she wants to know whether the DAQ changed. You open the release
notes: the update lowered the hardware energy threshold. Before this chapter that sentence
means nothing. After it, you know that a lower threshold lets through more photons that
scattered in the phantom, and that the energy window in the sorter should have removed
them. So the question is whether the window was applied before or after the multiples
policy, which decides what happens to a window with three singles in it. You run
MiniDAQ's simulator with both thresholds, count by truth, and have an answer by lunch:
yes, the order matters, and here are the numbers.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain positron emission, annihilation and the 511 keV photon pair, and compute with
   activities, half-lives and decay corrections.
2. Describe how 511 keV photons interact with tissue and with detector crystals
   (photoelectric absorption, Compton scattering, attenuation), and what that does to the
   measured energy.
3. Describe the detector chain from crystal to FPGA: scintillators (LYSO, BGO),
   photodetectors (SiPMs, PMTs), front-end ASICs and digitizers, and what each contributes
   to the event stream.
4. Define true, scattered, random and multiple coincidences, how each scales with
   activity, and how each affects the image.
5. Explain energy resolution, coincidence time resolution and time of flight, and the
   limits on spatial resolution: positron range, non-collinearity, crystal size and depth
   of interaction.
6. Explain why a brain-dedicated scanner differs from a whole-body scanner, and what that
   means for its DAQ.

## Prerequisites and estimated time {.unnumbered}

Chapters 1 and 2, in particular the MDQ-P1 format and the geometry. High-school physics is enough;
the chapter derives what it uses. Python 3 for Exercises 8.1 and 8.2. Reading: about 3 hours.
Exercises: 6 to 8 hours. Milestone: 4 hours.

## From a decay to two photons

### The intuition

A PET tracer is a molecule that the body uses, labeled with an atom that decays by
emitting a positron. The positron travels a short distance in tissue, slows down, and
annihilates with an electron. The two particles' mass becomes two photons of 511 keV
each (the rest energy of an electron), emitted in almost exactly opposite directions. The
scanner never sees the decay. It sees two photons arrive at two crystals at almost the same
time, and concludes that the decay happened somewhere on the line between them, the
*line of response* (LOR). Millions of LORs, corrected for everything that distorts them,
reconstruct into an image of where the tracer went.

Three facts drive the whole DAQ design. The photons are *two*, so detection needs both of
them: a *coincidence*. They are *simultaneous*, within the time it takes light to cross
the scanner, about a nanosecond. And they have a *known energy*, so a photon that arrives
with much less has lost energy on the way and probably changed direction.

### Tracers, half-lives and activity

The tracer that most PET scans use is [18F]FDG, fluorodeoxyglucose labeled with
fluorine-18. Cells take it up like glucose, so it maps glucose metabolism; in the brain
that is a map of neuronal activity. For dementia, tracers that bind to amyloid plaques
(florbetapir, florbetaben, flutemetamol) and to tau tangles (flortaucipir) show the
hallmark proteins of Alzheimer's disease directly. All of these are labeled with
fluorine-18.

[Activity]{.idx} is the number of decays per second, in becquerel (1 Bq = 1 decay/s). The
older unit, the curie, is still common in the United States: 1 mCi = 37 MBq. Activity
falls exponentially with the [half-life]{.idx} T½:

A(t) = A~0~ · 2^(−t / T½)

| Isotope | Half-life | Typical use (verify: for your clinic) |
|---|---|---|
| Fluorine-18 | 109.8 min | FDG, amyloid and tau tracers |
| Carbon-11 | 20.4 min | Research tracers (needs an on-site cyclotron) |
| Gallium-68 | 67.7 min | Oncology tracers, from a generator |
| Oxygen-15 | 2.04 min | Blood flow (water) |

Not every decay emits a positron: fluorine-18 does so in about 97% of decays (verify: the
nuclear data table you cite). In this book, "activity" means positron decays per second,
which is what the scanner can see.

**Worked example: why the DAQ sees a falling rate.** A brain FDG scan typically starts 30
to 60 minutes after an injection of a few hundred megabecquerels (verify: the EANM
procedure guideline for brain FDG PET, Guedj et al. 2022, for the actual ranges). During a
20-minute acquisition the activity falls by a factor of 2^(20/109.8) = 1.135, to 88% of
its value at the start. Rates of trues fall by the same factor; rates of randoms, which
grow with the square of activity (later in this chapter), fall by 1.135² = 1.29, to 78%. Every count-rate
dependent setting of the DAQ, and every dead-time correction, has to hold across that
range within one scan. For a carbon-11 scan of the same length the factor is
2^(20/20.4) = 1.97: the rate halves.

Decay correction is the inverse: a number of counts measured between t~1~ and t~2~ is
scaled to what it would have been at a reference time. That correction is applied in
reconstruction, but it needs the DAQ to record accurate start and stop times, in a
time base that does not drift. A list-mode file without a trustworthy acquisition start
time cannot be decay corrected (Chapter 12).

::: box-mistakes
- **Mixing up activity at injection, at scan start and at the time of the measurement.**
  Every activity in a log or a file needs its reference time.
- **Assuming one positron per decay.** The positron fraction differs between isotopes.
- **Computing decay with minutes in one place and seconds in another.** Keep times in one
  unit with the unit in the name, as MiniDAQ does with `Picoseconds`.
:::

## Photon interactions

### The intuition

On its way out of the head and into a crystal, a 511 keV photon can do three things that
matter. It can pass without interacting. It can be *absorbed* (photoelectric effect):
it gives all its energy to an electron and disappears. Or it can *scatter* (Compton
effect): it gives part of its energy to an electron and continues in a new direction,
with less energy. In tissue, which is mostly water, almost every interaction at 511 keV
is a Compton scatter. In a detector crystal made of heavy elements, photoelectric
absorption is much more likely, which is why those crystals are chosen.

### Compton scattering

The energy of the scattered photon follows from conservation of energy and momentum.
For a photon of energy E scattered through an angle θ:

E′ = E / (1 + (E / m~e~c²)(1 − cos θ))

For E = m~e~c² = 511 keV this simplifies to E′ = 511 keV / (2 − cos θ): no loss at 0°, half
the energy at 90°, a third (170 keV) for a photon scattered straight back. Which angles
are likely is given by the Klein-Nishina cross section. At 511 keV it strongly favors
small angles: most scattered photons keep most of their energy and change direction only
a little. That is the bad news for PET, because those photons look almost like
unscattered ones, in energy and in direction.

MiniDAQ's simulator uses both formulas directly:

```{.cpp include="minidaq/include/minidaq/sim/physics.hpp" snippet="compton"}
```

To draw scattering angles from the Klein-Nishina distribution, the simulator uses
rejection sampling. It proposes cos θ uniformly, which is uniform in solid angle, and
accepts the proposal with probability f / 2, where f never exceeds 2:

```{.cpp include="minidaq/src/sim/detector_simulator.cpp" snippet="kn"}
```

Exercise 8.4 has you write this sampler and prove it right with a chi-square test, and
explains why the obvious shortcut, isotropic scattering, gives a scatter fraction that
is too optimistic.

### Attenuation

The probability that a photon travels a distance x through a material without
interacting is e^(−μx), where μ is the linear attenuation coefficient. For water at 511 keV,
μ = 0.096 per cm (NIST XCOM / Hubbell and Seltzer tables, including coherent scattering):
half of the photons interact within 7.2 cm.

**Worked example: attenuation along a line of response.** A brain is roughly 18 cm
across. A decay at depth x on a line of response through 18 cm of tissue sends one photon
through x and the other through 18 − x. The probability that *both* escape without
interacting is e^(−μx) · e^(−μ(18−x)) = e^(−μ · 18) = 0.18, the same for every point on the
line. That is the property that makes PET quantitative: the attenuation of a coincidence
depends only on the line, not on where along it the decay happened, so it can be measured
(with a CT scan or a transmission source) and corrected exactly. It also says that over
80% of coincidences through the middle of a head lose at least one photon to an
interaction, most of them to a Compton scatter.

MiniDAQ tracks photons through a water cylinder with exponential free paths, using the
energy-dependent μ of water, interpolated from the NIST table, so that a scattered photon,
with less energy, is attenuated more. The geometry needs one function: where a ray leaves
a cylinder.

```{.cpp include="minidaq/include/minidaq/sim/physics.hpp" snippet="cylinder"}
```

### In the crystal

The crystal must stop the photon, preferably in one photoelectric absorption, so that the
light it produces measures the full 511 keV. Stopping power depends on density and atomic
number; lutetium (Z = 71) and bismuth (Z = 83) are the heavy elements of the two common PET
scintillators. A photon that Compton scatters in the crystal and then escapes deposits
only the energy of the recoil electron, from 0 up to the *Compton edge*, 341 keV for a
511 keV photon (the deposit when it scatters straight back). In the energy spectrum that
shows up as a continuum below the photopeak.

The simulator models the crystal with an attenuation coefficient (0.087 per mm for LYSO at
511 keV, used for all energies: a simplification) and a *photofraction*, more exactly the
full-energy or photopeak fraction: the probability that an interacting photon deposits its full
energy in the crystal. It is larger than the photoelectric fraction (about a third for LYSO at
511 keV, verify against the attenuation tables of NIST XCOM) because a photon that Compton
scatters first and is then absorbed in the same crystal also lands in the photopeak. The rest
deposit the recoil energy of one Compton scatter. That is two numbers instead of a transport
code, and enough to produce a realistic-looking spectrum (the figure below). The photofraction
of 0.6 is a modeling choice, not a measurement (assumption: confirm with team for your scanner's
crystals).

![Energy spectrum of 0.2 s of simulated singles (5 MBq in a water cylinder, `minidaq_sim`). Stacked: singles whose photon scattered in the phantom (orange) and those whose photon did not (blue). The photopeak at 511 keV is blurred by the 12% energy resolution; the blue continuum below 341 keV is Compton scatter in the crystal; most of the orange is scatter in the phantom, which the window removes, but not all of it. Figure generated by `book/tools/figures/ch08_energy_spectrum.py`.](src/img/ch08-spectrum.png){width=100%}

::: box-mistakes
- **Treating "scattered" as "low energy".** A photon that scattered through 25° keeps
  467 keV and passes any reasonable energy window. Energy windows reduce scatter;
  they do not remove it.
- **Confusing scatter in the patient with scatter in the crystal.** Both lower the
  measured energy. Only the first moves the line of response far; the second blurs the
  position by a crystal or two, and in some detectors deposits energy in two crystals
  (inter-crystal scatter).
- **Using the 511 keV attenuation coefficient for a scattered photon.** At 300 keV, water
  attenuates about 23% more.
:::

## The detector chain

### The intuition

A detector turns a photon into numbers in four steps. A *scintillator crystal* absorbs
the photon and emits a short flash of visible light. A *photodetector* turns the light
into an electrical pulse. A *front-end ASIC* (an application-specific integrated circuit)
measures when the pulse started and how large it was. A *digitizer and an FPGA*
assemble those measurements into event words and send them over a link. Each step adds
noise to the time and to the energy, and each step has a maximum rate.

### Scintillators

| Property | LSO/LYSO | BGO |
|---|---|---|
| Density | about 7.1 to 7.4 g/cm³ | 7.13 g/cm³ |
| Light yield | about 30,000 photons/MeV | about 8,000 photons/MeV |
| Decay time | about 40 ns | about 300 ns |
| Intrinsic radioactivity | yes (lutetium-176) | none |
| Typical use | time-of-flight PET | high-sensitivity, non-TOF PET |

The values are typical; light yield in particular depends on the growth and the
co-doping (verify: your crystal supplier's data sheet). Two consequences reach the DAQ
directly. The *decay time* sets how long a crystal is busy with one photon, and so the
dead time and pile-up at high rates (Chapter 11). The *intrinsic radioactivity* of
lutetium means that an LYSO scanner sees singles even with no patient in it: a background
that the DAQ records, a few hundred becquerels per cubic centimeter of crystal (verify:
supplier data), which is useful for calibration and must not be mistaken for a fault.

### Photodetectors

Photomultiplier tubes (PMTs) amplify a few photoelectrons into a large pulse, with a gain
around a million, but they are bulky, need high voltage, and do not work in a magnetic
field. *Silicon photomultipliers* (SiPMs) are arrays of thousands of tiny avalanche
photodiodes, each operated above breakdown so that one photon fires it completely; the
sum of the fired cells is the signal. SiPMs are compact, work at tens of volts, are
insensitive to magnetic fields (so they work inside an MR scanner), and are fast. Their
gain and dark count rate depend strongly on temperature, which is why a SiPM-based
scanner monitors temperatures and corrects gains: a calibration problem that becomes a
DAQ data stream (Chapter 26).

### Front-end ASICs and the FPGA

A front-end ASIC serves many channels. For each pulse it produces a *timestamp*,
typically from a time-to-digital converter that combines a coarse clock counter with a
fine interpolation, and an *energy*, from integrating the charge or from measuring
*time over threshold*, how long the pulse stays above a level. PETsys's TOFPET2, a
commercial ASIC used in PET research, is a documented example of this design (Chapter 9
looks at its output). An FPGA on each board collects the ASIC outputs, applies first
corrections, packs event words and sends them to the acquisition PC, usually over Gigabit
or 10 Gigabit Ethernet.

Where the coincidence decision happens is an architecture choice. Older scanners formed
coincidences in hardware, in a central trigger unit, and sent only pairs. Many modern
systems send every single that passes a threshold and form coincidences in software on
the acquisition PC. That puts the sorter, and its throughput, in your hands (Chapter 10).
MiniDAQ follows the second design; which one your scanner uses is a question for the team.

::: box-mistakes
- **Assuming the ASIC's energy is in keV.** It is in ADC units or time-over-threshold
  ticks, nonlinear, and different for every channel. Energy calibration (Chapter 26) maps
  it to keV; the DAQ must know which it is carrying.
- **Ignoring the background.** An LYSO scanner is never silent; a DAQ test that expects
  zero singles without a source fails on real hardware.
- **Forgetting temperature.** SiPM gain drifts with temperature; a DAQ that does not
  record temperatures with the data makes some calibration problems undiagnosable.
:::

## Event types and how they scale

### The intuition

Every pair of singles that the sorter accepts as a coincidence is called a *prompt*. Some
prompts are what you want; others are noise that looks the same to the sorter. The truth
classes are:

- A **true** coincidence: both photons from one decay, neither scattered. Its LOR passes
  through the decay.
- A **scattered** coincidence: both photons from one decay, at least one scattered in the
  patient. Its LOR is wrong, often by centimeters.
- A **random** coincidence: two photons from two different decays that happened to arrive
  within the window. Its LOR has nothing to do with either decay.
- A **multiple**: three or more singles within one window. Which pair, if any, to keep is a
  policy decision (Chapter 10).

The sorter cannot tell these apart from one pair; only statistics can. Randoms can be
estimated with a *delayed window*, which pairs singles with others shifted by much more
than any true time difference (Chapter 10). Scatter is estimated in reconstruction from a
model.

### How each scales with activity

Trues and scatters come from single decays, so their rates are proportional to the
activity A. Randoms need two independent decays, so their rate is proportional to the
product of two singles rates, each proportional to A: randoms grow with A². For two
detectors with singles rates S~1~ and S~2~ and a window |Δt| ≤ τ:

R = 2τ S~1~ S~2~

Exercise 8.3 derives this and checks it against a simulation. Its consequences are the
reason the coincidence window matters so much: randoms are proportional to τ, and the
ratio of randoms to trues grows linearly with activity.

**Worked example: two detectors at 1 M singles/s.** With τ = 4 ns:
R = 2 × 4 × 10^−9^ s × 10^6^ /s × 10^6^ /s = 8,000 randoms per second between those two
detectors. A whole scanner has many detector pairs, and the ratio is what matters: at
the activity where randoms equal trues, half of the prompts carry no information, and
their subtraction adds noise to the image. Exercise 8.5 finds that activity for MiniDAQ's
phantom with a 10 ns window: near 19 MBq.

### Measured with MiniDAQ's simulator

The simulator described in the next section counts every class by truth. For a uniform
cylinder of activity (radius 80 mm, length 100 mm) inside a water cylinder (radius 90 mm,
length 180 mm), 5 MBq, 1 second, a 4 ns window:

| Energy window | Trues /s | Scatters /s | Randoms /s | Multiples /s | Scatter fraction |
|---|---|---|---|---|---|
| 100 to 1000 keV | 100,427 | 186,472 | 11,043 | 3,982 | 0.650 |
| 435 to 650 keV | 47,362 | 17,098 | 3,007 | 462 | 0.265 |

The *scatter fraction* is S / (T + S). The energy window cuts it from 65% to 27%, at the
cost of half of the trues: both photons of a true must deposit their full energy, and
with a photofraction of 0.6 only about 0.6² of true pairs do. Exercise 8.5 measures how
each rate grows with activity, and Chapter 11 turns these rates into the noise-equivalent
count rate (NECR), the number that tells you which window is best.

::: box-mistakes
- **Calling every prompt a true.** A prompt count is trues plus scatters plus randoms.
  Report which one a number is.
- **Testing a sorter at one activity.** Randoms and multiples grow faster than trues; a
  sorter that is right at 1 MBq can be wrong, or slow, at 20 MBq.
- **Estimating randoms with the same window as the prompts, shifted by too little.** A
  delayed window must be shifted by more than the largest true time difference plus the
  time resolution, or it counts trues.
:::

## Energy, time and position: the resolution budget

### The intuition

Each measurement has an uncertainty. *Energy resolution* decides how well the energy
window separates scattered from unscattered photons. *Time resolution* decides how narrow
the coincidence window can be, and, if it is good enough, where along the LOR the decay
happened: time of flight. *Spatial resolution* decides how small a structure the image can
show, and has physical limits that no software can remove.

### Energy resolution

Energy resolution is the full width at half maximum (FWHM) of the photopeak divided by
its energy. LYSO detectors reach about 10 to 12% at 511 keV (verify: for your scanner's
detectors). The photopeak's standard deviation is σ = FWHM / 2.355, so 12% at 511 keV is
σ = 26 keV. The simulator assumes the resolution scales as 1/√E, as photon counting
statistics would give:

σ(E) = R~511~ · √(511 keV · E) / 2.355

Exercise 8.2 turns a resolution into an energy window and shows why the window is
asymmetric around 511 keV.

### Coincidence time resolution and time of flight

The *coincidence time resolution* (CTR) is the FWHM of the distribution of measured
t~1~ − t~2~ for true coincidences from a point source at the center. Modern clinical
time-of-flight scanners reach a few hundred picoseconds (verify: the vendor's NEMA
results for the scanners you compare with).

Time of flight uses the time difference to locate the decay along the LOR. A decay at
distance x from the midpoint arrives Δt = 2x / c earlier at the nearer crystal, so
x = c Δt / 2. With c = 0.3 mm/ps, a CTR of 300 ps localizes the decay to
0.3 × 300 / 2 = 45 mm FWHM. That is far from a point, but much better than "somewhere
along 18 cm of head". The gain in image signal-to-noise ratio is roughly √(D / Δx), where
D is the size of the object and Δx the TOF localization: for a head (D ≈ 18 cm) and
300 ps (Δx = 4.5 cm), about 2. For a whole body (D ≈ 40 cm) the same CTR gives about 3,
which is why time of flight matters more in large patients (Conti 2009).

The simulator gives each single half of the pair's time variance, so that the
difference of a true pair has the configured CTR as its FWHM. The test
`DetectorSimulator.CoincidenceTimeResolution` measures it:

| Simulated quantity | Configured | Measured (test) |
|---|---|---|
| Energy resolution at 511 keV | 12.0% | 12.0% ± 0.3% |
| CTR | 300 ps | 300 ps ± 10 ps |
| Photons entering the ring, point source at the center | 36.5% (analytic) | within 0.5% |

### Spatial resolution

Four effects limit spatial resolution, each independent of the others, so they add in
quadrature (Moses 2011):

- **Positron range.** The positron travels before it annihilates. For fluorine-18 the
  effect is small, a fraction of a millimeter (verify: Levin and Hoffman 1999 give the
  distribution); for higher-energy positron emitters it is millimeters.
- **Non-collinearity.** The two photons are not exactly back to back, because the
  positron and electron are not at rest when they annihilate. The deviation is about
  0.5° FWHM, which blurs the position at the center by about 0.0022 × D, where D is the
  ring diameter: 0.66 mm for a 30 cm ring, 1.8 mm for an 80 cm whole-body ring.
- **Crystal size.** A crystal of width d contributes about d / 2.
- **Depth of interaction and parallax.** A photon that enters a crystal at an angle can
  interact deeper, in the next crystal along its path. Without a measurement of the depth
  of interaction (DOI), the position is wrong by an amount that grows with the distance
  from the center of the ring and with the crystal length.

**Worked example: the resolution of MiniDAQ's geometry.** With 2.45 mm crystals, a 30 cm
ring, fluorine-18 and a reconstruction factor of about 1.25 (Moses 2011 uses this
empirical form):

R ≈ 1.25 · √((2.45/2)² + (0.0022 · 300)² + r²) mm

With the positron range r taken as 0.2 mm (an assumption; the distribution is not
Gaussian), R ≈ 1.25 · √(1.50 + 0.44 + 0.04) = 1.76 mm at the center, before the
detector's own position decoding errors. The crystal term dominates; non-collinearity is
the second term, and it is a reason to build brain scanners small. At the edge of the
field of view, parallax adds to this unless the detector measures DOI.

The simulator models non-collinearity (as two perpendicular Gaussian deviations of 0.5°
FWHM) and parallax (the crystal is the one containing the interaction point, not the
entry point), and leaves out positron range. Its model card below lists all of it.

::: box-mistakes
- **Quoting the CTR of a single detector as the scanner's.** CTR is a property of a pair;
  a single detector's time resolution is about CTR / √2.
- **Forgetting that CTR includes the electronics.** The ASIC, the clock distribution and
  the time calibration all add to it. A DAQ that adds 100 ps of jitter to timestamps
  degrades a 200 ps system measurably.
- **Using FWHM and σ interchangeably.** FWHM = 2.355 σ for a Gaussian. Write which one a
  number is, in the variable name if you can (`ctr_fwhm_ps`).
:::

## The detector simulator

### The intuition

Every algorithm in Part II needs test data with known answers: a sorter must find the
trues, a randoms estimate must match the real randoms, a count-rate curve must have the
right shape. Real data has no labels. A Monte Carlo simulator does: it knows, for every
single, which decay produced it and whether its photon scattered. MiniDAQ's simulator is
small enough to read in an evening and good enough to give the effects of this chapter the
right shape and order of magnitude. It is not a substitute for a validated simulation
toolkit such as GATE (Jan et al. 2004) when the numbers inform a decision about the real
scanner.

### What it does

The configuration names the source, the phantom and the detector model:

```{.cpp include="minidaq/include/minidaq/sim/detector_simulator.hpp" snippet="config"}
```

Decays arrive as a Poisson process at the configured activity. Each decay emits two
photons from a point sampled in the source. Each photon is tracked through the phantom,
to the ring, and into a crystal:

```{.cpp include="minidaq/src/sim/detector_simulator.cpp" snippet="track"}
```

Every single carries its truth, which is the point of the whole exercise:

```{.cpp include="minidaq/include/minidaq/sim/detector_simulator.hpp" snippet="truth"}
```

### Time order

A sorter needs its input in time order, and a simulator produces singles in decay order.
The two are not the same: a photon's flight time (around half a nanosecond to the ring,
more after a scatter) and the time blur
(clamped to ±6σ) move singles relative to the decay that produced them. The simulator
keeps a small min-heap of pending singles and releases one only when no future decay can
produce an earlier one:

```{.cpp include="minidaq/src/sim/detector_simulator.cpp" snippet="order"}
```

The test `OutputIsTimeOrderedAndValid` checks 100,000 singles at 20 MBq. The clamp at 6σ
changes the time distribution by less than one single in 10^8^, and it is what makes the
bound exist; an unbounded Gaussian would make "no earlier single can come" impossible to
prove.

### Counting by truth

`count_coincidences` is a deliberately simple reference: a fixed window opened by the
first single not yet used, energy window first, no geometry cuts. A window with exactly two
singles is a coincidence, classified from the truth; a window with more is a multiple.

```{.cpp include="minidaq/src/sim/truth_counter.cpp" snippet="window"}
```

It is the yardstick for Chapter 10's sorter, not a sorter itself: it ignores
geometry, has one multiples policy (discard), and keeps everything in memory.

### The model card

A simulator's assumptions belong in one place, next to its code, so that nobody uses it for
something it cannot do. MiniDAQ's:

| Modeled | Left out |
|---|---|
| Poisson decays, point and uniform cylinder sources | Positron range; positron fraction (every decay emits a pair) |
| Non-collinearity, 0.5° FWHM | Decay of the source during the run |
| Compton scatter in water, Klein-Nishina angles, energy-dependent attenuation | Photoelectric absorption and Rayleigh scattering as separate processes in water (their attenuation is in μ, and every interaction is treated as Compton) |
| One ring of crystals with depth of interaction (parallax) | Gaps between blocks, inter-crystal scatter, light sharing |
| Crystal attenuation (one μ for all energies) and a photofraction | Crystal energy dependence, the Compton continuum of multiple interactions |
| Gaussian energy blur (1/√E) and time blur (CTR) | Dead time, pile-up, time walk, ASIC nonlinearity (Chapters 9 and 11) |
| Energy threshold | Lutetium background, dark counts, electronic noise |

Its speed is about 0.85 M decays per second on one core of the book's machine (`release`
preset, 5 MBq for 1 s took 5.9 s), slower than real time above about 1 MBq. That is fine
for tests and for generating input files; Chapter 10's throughput tests use recorded
streams.

::: box-mistakes
- **Testing an algorithm with data from the same assumptions as the algorithm.** If the
  sorter and the simulator both assume back-to-back photons, the test cannot find a sorter
  that fails without them. Keep the simulator's physics independent of the code under
  test, and look at the truth, not only at counts.
- **Believing simulated rates.** They have the right shape and the right order of
  magnitude. The absolute sensitivity of a real scanner comes from a NEMA measurement
  (Chapter 11).
- **A simulator without a seed.** Every test that uses it must be reproducible; MiniDAQ's
  is deterministic for a seed and a standard library implementation.
:::

## Brain PET

### Why a dedicated scanner

A whole-body PET scanner has a ring of about 70 to 80 cm diameter, large enough for any
patient. For the brain, most of that ring is far away from the organ. A ring sized for the
head brings the crystals closer: each crystal covers a larger solid angle, so the same
number of crystals gives more sensitivity; the non-collinearity blur, proportional to the
ring diameter, shrinks; and the scanner is smaller, lighter and cheaper, which makes it
possible to place one where a whole-body PET/CT would not fit or pay off. The price is
parallax: in a small ring, more lines of response cross crystals at steep angles, so
depth of interaction matters more.

The clinical case is dementia. FDG shows the patterns of reduced metabolism that
distinguish types of dementia; amyloid and tau tracers show the proteins of Alzheimer's
disease. With treatments that target amyloid now approved in some markets, the number of
patients who need a brain PET to confirm amyloid before treatment is growing (verify:
current approvals and guidelines in your markets). Compact, brain-dedicated PET
scanners are designed for that use. This book does not describe any product's internal
design; read your manufacturer's own publications and ask your team which to read first.

### What it means for the DAQ

A compact scanner with fewer crystals produces lower total singles rates than a
whole-body scanner, but the rates per crystal can be high, because each crystal is close
to the activity. Time-of-flight gains are smaller for a head than for a body, so a brain
scanner may trade some timing resolution for cost; the coincidence window and the DAQ's
time calibration follow from that choice. DOI, if the detector measures it, adds a field to
every event word and a calibration to the pipeline. The answers depend on your scanner's
detector design, which is why the first question for the team below is about the event
word.

::: box-regulated
The physics in this chapter becomes regulated content in three places.

- **Performance claims.** Spatial resolution, sensitivity, count-rate performance and
  image quality in labeling and submissions come from standardized measurements (NEMA NU 2,
  Chapter 11) on the real scanner, not from simulations or textbook formulas. A simulator
  supports the design; it is not evidence of performance.
- **Software tools used for verification.** If a simulator generates the expected results
  of verification tests (for example, the sorter's validation in Chapter 10), it is a tool
  whose fitness for that purpose must be justified: what it models, how it was checked, and
  under which configuration. The model card and the simulator's own tests are the start of
  that record (tool confidence, Chapter 20).
- **Simulated data must never look like patient data.** List-mode files written from
  simulations carry a header field that says so (Chapter 12), and they never contain
  patient identifiers.
:::

::: box-askteam
1. What exactly does your scanner's event word contain (time, energy, crystal or pixel, DOI),
   in which units, and where is its specification? Who owns it?
2. Which scintillator and photodetector does your scanner use, and what are its measured energy
   resolution, CTR and photofraction? Which numbers in this chapter's simulator are far
   off?
3. Are coincidences formed in hardware (FPGA) or in software on the acquisition PC? If in
   software, what are the default time and energy windows, and how were they chosen?
4. Does the detector measure depth of interaction? If so, how is it encoded and
   calibrated?
5. Which simulation toolkit (GATE or another) does the physics team use, and which of its
   outputs does the DAQ team use to test the sorter?
:::

## Exercises {.unnumbered}

**Exercise 8.1 (E): The coincidence time window for a 30 cm ring.** *Goal:* compute the
window width that loses no true coincidence for photons that can cross the full ring
diameter, then add the timing resolution and compute how many trues a window keeps.
*Starter:* `exercises/ch08/e1_time_window/` (Python). *Acceptance:*
`tests/test_time_window.py` passes: 1000.7 ps for 300 mm, a 2,766 ps window for 300 ps CTR
at 3σ, the probability of keeping a true at the window's edge; a comment on what could
justify the 4 ns MiniDAQ uses, and what the extra width costs. *Time:* 30 minutes.

**Exercise 8.2 (E): An energy window for 10% resolution.** *Goal:* given 10% energy
resolution at 511 keV, choose an energy window and justify both edges: the photopeak
fraction each keeps, and the smallest scatter angle the lower edge rejects. *Starter:*
`exercises/ch08/e2_energy_window/` (Python). *Acceptance:* `tests/test_energy_window.py`
passes: σ = 21.7 keV, the Compton formula, 30.2° for a 450 keV edge, a window with at
least 95% of the photopeak inside 425 to 650 keV for 10% and 15% resolution; two sentences
on asymmetry and on why scatter still passes. *Time:* 45 minutes.

**Exercise 8.3 (M): The randoms rate, derived and measured.** *Goal:* derive
R = 2τ S~1~ S~2~, estimate it for two detectors at 1 M singles/s with a 4 ns window, and check
it by counting chance pairs between two simulated, independent streams. *Starter:*
`exercises/ch08/e3_randoms/` (a pair counter that looks only forward in time, a formula off
by a factor). *Acceptance:* `tests/test_randoms.cpp` passes: exact counts on hand-made
streams, the measured rate within 4 standard deviations of the formula, linear running
time; the derivation in five lines in `NOTES.md`. *Time:* 1.5 hours.

**Exercise 8.4 (M, extra): Sampling Compton scattering.** *Goal:* the Compton energy formula
and a Klein-Nishina sampler, proven right statistically. *Starter:*
`exercises/ch08/e4_klein_nishina/` (a sign error and isotropic scattering). *Acceptance:*
`tests/test_compton.cpp` passes: kinematics at 0°, 90° and 180°, chi-square below 80 for 39
degrees of freedom at 511 and 140 keV with 400,000 samples, the forward fraction within
0.005. *Time:* 1.5 hours.

**Exercise 8.5 (M, extra): Trues, scatters and randoms versus activity.** *Goal:* sweep the
simulator's activity from 1 to 8 MBq, count every class by truth, and fit power laws.
*Starter:* `exercises/ch08/e5_rates_vs_activity/` (the sweep is a TODO; the fit is a straight
line through raw values). *Acceptance:* `tests/test_rates.cpp` passes: exact power laws
recovered, exponents within 0.05 of 1 for trues and scatters and within 0.1 of 2 for randoms,
a sensitivity 2 to 10% lower at 8 MBq than at 1 MBq, a rising randoms fraction; in
`NOTES.md`, why the sensitivity falls and where randoms would equal trues. *Time:* 2 hours.

## MiniDAQ milestone: the detector simulator {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ can generate a realistic, time-ordered stream of singles from a source in a
phantom, with ground truth for every single, and count trues, scatters, randoms and multiples
by truth. **Start:** tag `ch07`. **End:** tag `ch08`.
:::

1. Add `minidaq/include/minidaq/sim/physics.hpp` (Compton kinematics, Klein-Nishina shape,
   water attenuation, ray geometry) with `test_physics.cpp`.
2. Add `DetectorSimulator` (`sim/detector_simulator.hpp` and `.cpp`): configuration and
   validation, decays, transport through the phantom, detection with parallax, energy and
   time blur, threshold, time-ordered output, statistics.
3. Add `count_coincidences` (`sim/truth_counter.hpp` and `.cpp`).
4. Add `test_detector_simulator.cpp`: invalid configurations (NaN in any field included) rejected, determinism, time
   order, decay rate, axial acceptance against the analytic value, energy resolution, CTR,
   scatter rejected by the energy window, trues linear and randoms quadratic in activity.
5. Add the tool `minidaq_sim` (statistics, counts by truth, optional MDQ-P1 words and a truth
   CSV) and the figure script `book/tools/figures/ch08_energy_spectrum.py`.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `tools/static_analysis.sh`
reports nothing; `architecture.layers` passes (the simulator is in the core layer and uses no
I/O); `minidaq_sim --activity 5e6 --seconds 1` reports a scatter fraction between 0.2 and 0.35
in the 435 to 650 keV window. Tag `ch08`.

## Check yourself {.unnumbered}

1. Why are randoms proportional to the square of activity while trues are linear?
2. What does time of flight buy you in image quality, and why less in a head than in a body?
3. A 20-minute FDG scan: by how much do the trues rate and the randoms rate fall from start
   to end, and why does that matter for the DAQ?
4. Why does attenuation along a line of response not depend on where the decay happened,
   and why does that make PET quantitative?
5. A photon scatters through 25° in the patient. What energy does it keep, and does a 435 keV
   lower threshold reject it?
6. What is the Compton edge for 511 keV photons, and what part of the energy spectrum does it
   bound?
7. Name the four physical limits on spatial resolution. Which one grows with the ring
   diameter, and which one gets worse in a small ring?
8. Why is LYSO preferred for time-of-flight PET, and what does its intrinsic radioactivity
   mean for the DAQ?
9. With a photofraction of 0.6, what fraction of true pairs can pass a photopeak-only energy
   window, and what happens to the rest?
10. Why does MiniDAQ's simulator hold singles in a heap before returning them, and what
    makes it safe to return one?
11. Name two things the simulator leaves out that would change the count-rate curves of
    Chapter 11, and how each would change them.

## Summary {.unnumbered}

- PET detects the two 511 keV photons of an annihilation in coincidence; the decay lies on
  the line of response between the two crystals.
- Activity falls with the isotope's half-life during a scan; trues follow it linearly,
  randoms with its square.
- In tissue, 511 keV photons mostly Compton scatter; attenuation along a line of response
  is independent of the decay's position, which makes it correctable.
- Crystals (LYSO, BGO), photodetectors (SiPMs, PMTs), ASICs and FPGAs each add noise to time
  and energy and each have a maximum rate.
- Prompts are trues plus scatters plus randoms; multiples need a policy. R = 2τ S~1~ S~2~.
- Energy resolution sets how well the window rejects scatter; CTR sets the window and the
  time-of-flight gain; positron range, non-collinearity, crystal size and parallax limit
  spatial resolution.
- A brain-dedicated scanner trades a smaller ring and higher sensitivity per crystal for more
  parallax and smaller time-of-flight gains.
- MiniDAQ's detector simulator produces time-ordered singles with ground truth; its model
  card says what it cannot be used for.

## Further reading {.unnumbered}

- S. R. Cherry, J. A. Sorenson, M. E. Phelps, *Physics in Nuclear Medicine*, 4th ed.,
  Elsevier Saunders, 2012: the chapters on interactions of radiation with matter,
  scintillation detectors and PET.
- D. L. Bailey, D. W. Townsend, P. E. Valk, M. N. Maisey (eds.), *Positron Emission
  Tomography: Basic Sciences*, Springer, 2005.
- W. W. Moses, "Fundamental limits of spatial resolution in PET", *Nuclear Instruments and
  Methods in Physics Research A* 648 (2011) S236–S240.
- C. S. Levin, E. J. Hoffman, "Calculation of positron range and its effect on the
  fundamental limit of positron emission tomography system spatial resolution", *Physics
  in Medicine and Biology* 44 (1999) 781–799.
- M. Conti, "State of the art and challenges of time-of-flight PET", *Physica Medica* 25
  (2009) 1–11.
- D. R. Schaart, "Physics and technology of time-of-flight PET detectors", *Physics in
  Medicine and Biology* 66 (2021) 09TR01.
- O. Klein, Y. Nishina, "Über die Streuung von Strahlung durch freie Elektronen nach der
  neuen relativistischen Quantendynamik von Dirac", *Zeitschrift für Physik* 52 (1929)
  853–868.
- J. H. Hubbell, S. M. Seltzer, *Tables of X-Ray Mass Attenuation Coefficients and Mass
  Energy-Absorption Coefficients*, NIST Standard Reference Database 126,
  <https://physics.nist.gov/PhysRefData/XrayMassCoef/>.
- S. Jan et al., "GATE: a simulation toolkit for PET and SPECT", *Physics in Medicine and
  Biology* 49 (2004) 4543–4561.
- E. Guedj et al., "EANM procedure guidelines for brain PET imaging using [18F]FDG,
  version 3", *European Journal of Nuclear Medicine and Molecular Imaging* 49 (2022)
  632–651.
