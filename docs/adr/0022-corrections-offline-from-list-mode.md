# 0022. Corrections computed after the acquisition from the list mode and the run record

Date: 2026-11-03
Status: Accepted

## Context

The counts of a line of response are not the activity along it. They are reduced by attenuation
and by each crystal's efficiency, and increased by random and scattered coincidences; dead time
and decay change them with the count rate and the time. A reconstruction needs each of these
corrections, and each one needs something from the acquisition: the coincidences, the singles
rates, the windows the sorter used, the calibration table, the timing of the run. Three
questions:

- where the corrections are computed: in the server during the run, or after it, from what the
  run wrote;
- what the acquisition must record for them, and how a correction is tied to the data it
  corrects;
- which methods: how the randoms are estimated, how the normalization is factored, where the
  attenuation and the scatter come from.

## Options

Where:

1. **In the server, during the run.** Corrected sinograms come out of the acquisition. The
   server would hold models of the patient (attenuation, scatter) that the DAQ team cannot
   validate, and every change of method would be a change of the class B server.
2. **After the run, by a separate tool**, from the list-mode files and a run record that carries
   what the files do not. The server records; the physicists' tool computes; the record ties
   them together.

The randoms: the delayed window (a second sorter window shifted by 100 ns), its counts smoothed by
variance reduction, or the singles rates, `2 tau S_a S_b`. The normalization: a direct
measurement of every line (a scan of hundreds of millions of counts), or component-based,
crystal efficiencies times geometric factors. The attenuation: a CT or MR image, or a calculated
outline. The scatter: a Gaussian fitted to the tails of the projection, or a model's shape (single
scatter simulation, Monte Carlo) scaled to the tails.

## Decision

Option 2. The pipeline counts the singles in the energy window per crystal and every single per
block (SRS-COR-001); the run record carries them with the windows, the window mode and the
numbers of prompts and delayeds (SRS-COR-002, the `corrections` object of the run record). The
corrections tool, `tools/recon` (TL-30, class T3, numpy only as `tools/calib`), reads the
list-mode files and the record, bins the coincidences exactly as `minidaq_listmode sino`, and
refuses a normalization whose windows or calibration table differ from the run's (SRS-COR-003).

- Randoms from the singles, with each crystal's singles that are already in a prompt coincidence
  taken out: under the kill-all rule (Chapter 10) a paired single cannot also make a random pair.
  Against the simulator's truth: -1.8%, where all singles give +31.1% and the delayed window
  +7.1% (measurements/ch27). The delayeds stay in the list mode as a check.
- Component-based normalization: crystal efficiencies from the fan sums of a scan of a cylinder in
  air (prompts minus delayeds), geometric factors from the same scan divided by the efficiencies
  and the source's chords. Six runs of 5 s at 10 MBq give the efficiencies to 3.4% rms per crystal
  and 1.4% per bin.
- Calculated attenuation of a water outline, `mu = 0.0096 / mm`. A CT image is the better input
  where the scanner has one; a calculated outline is what a head scanner without one uses.
- Scatter from a model's shape scaled to the projection's tails, with the scale the Poisson
  maximum likelihood of the tail counts. A Gaussian fitted to the tails gives 2.4 times the
  scatter under the object: the tails of a head are short and window-limited, and a Gaussian
  extrapolated from them is not the shape inside.
- Whole-run totals only. A dynamic study needs the singles per frame; the record has no frames
  yet (assumption: confirm with team whether frames belong in the acquisition or in the tool).

## Consequences

### Positive

- The server's change is small and testable: a counter and a record. The models of the patient
  stay with the team that validates them, and a change of method is a change of a tool, not of
  the server.
- A correction names its inputs: the normalization and the run both carry their windows and their
  calibration table, and the tool refuses a pair that differs (H-12, RC-39 and RC-40).
- Every correction is measured against the simulator's truth (measurements/ch27): the profile of a
  water phantom is flat within 1.9% rms after all corrections, against 1.1% for the truth's own
  noise.

### Negative

- The corrections depend on models that no test of the software can validate: the outline of the
  head, the scatter model's shape, the dead-time model's kind. They are the residual of H-12, and
  the validation with phantoms (Chapter 30) is their control.
- The scatter estimate rests on the tails, where the randoms are nearly six times the scatter: a
  2.3% error of the randoms there is a 13% error of the scatter (1.14 times the truth). One scale
  per slice is 42% noisy at the counts of the measurement; one scale for all slices is 14% per
  slice.
- The singles counter adds a relaxed atomic load and store per single to the decode stage. It is
  inside the noise of the pipeline benchmark (27 to 28 M singles/s with it, 22 to 29 without,
  measurements/ch27/singles-counter-cost.txt), but it is one more thing on the hot path.
- Whole-run singles cannot correct a frame of a dynamic study.
