# Exercise 27.1: notes on the solution

**The three mistakes.**

- *A fan sum is not an efficiency unless every crystal sees the same thing.* On average
  `F[i] = eff[i] * sum_j eff[j] expected[i, j]`. The starter took `F[i] / mean(F)`, which assumes
  the sum is the same for every crystal. Off center, the crystals near the source see longer
  chords through it, so their fan sums are higher whatever their efficiency: the starter's
  efficiencies were 21% wrong rms. The solution iterates `eff[i] = F[i] / sum_j eff[j]
  expected[i, j]`, which divides out the source's own pattern and the partners' efficiencies.
- *The partners matter on a small scanner.* Even centered, the sum includes the efficiencies of
  the crystal's partners. Here each crystal has about 100 partners whose lines cross the source (25
  positions across the ring, in 4 rings), with efficiencies that spread 5.6% relative to the
  mean: their mean varies by about 0.56% from crystal to crystal, which adds to the Poisson error
  of 0.5% (the starter's error was 0.71% rms, the limit 0.65%). In MiniDAQ a crystal of the
  normalization scan has about 10,000 partners and the term is 0.05%, which is why `tools/recon`
  can take one step.
- *A line's efficiency is the product of its crystals'.* A coincidence needs both photons to be
  detected, each with its crystal's probability, so the line's efficiency is `eff[i] * eff[j]`.
  The mean `(eff[i] + eff[j]) / 2` divides by too little and leaves half of each crystal's
  deviation in the data: the fan sums of the normalized scan kept a 2.9% pattern.

A dead crystal needs a decision, not arithmetic: its lines measured nothing, and dividing by zero
efficiency would make them infinite. The solution sets them to 0 and names the crystal, so that a
reconstruction can leave the lines out rather than read them as zero activity.

**Counts** (Then, by hand, 1). The fan sum's Poisson error is `1 / sqrt(F)`: 1% needs 10,000
counts per crystal, about 92 million coincidences for 18,432 crystals (each coincidence is in two
fans). The simulator's normalization scan gave 10.5 million prompts in six runs of 5 s at 10 MBq,
350,000 prompts per second: 92 million would take about 260 s of acquisition. A real normalization
source of a few tens of MBq gives a similar rate, and a site acquires for hours, for this reason
(assumption: confirm with team how long your normalization scan is).

**The small scanner** (2). The one-step ratio leaves `mean_j eff[j]` over each crystal's
partners in the result. Its spread is the efficiencies' spread over the square root of the number
of partners: 5.6% / sqrt(100) = 0.56% here, 5.5% / sqrt(10,000) = 0.055% for MiniDAQ, where
the cylinder of radius 118 mm pairs a crystal with about 220 positions across the ring in each of
48 rings.

**Recalibration** (3). The efficiency of a crystal is the share of its photons that land in the
energy window. A new energy calibration moves each crystal's photopeak relative to the window by
a different amount, so each crystal's efficiency changes by a different amount, and the old
normalization no longer matches. The run record names the calibration table (SRS-CAL-005), and
the corrections tool refuses a normalization whose record names another table, energy window or
coincidence window than the run's (SRS-COR-003, risk control RC-40).
