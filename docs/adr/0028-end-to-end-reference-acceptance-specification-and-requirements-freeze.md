# 0028. The chain checked end to end against an offline reference, a written acceptance specification, and a requirements freeze

Date: 2026-11-04
Status: Accepted

## Context

By the end of Part VII every stage of MiniDAQ had its own tests, its own measurements and its own
chapter: the simulator, the readout link, the server's pipeline and sorter, the list-mode writer,
the sinograms, the corrections, the reconstruction and the QC report. The system tests of Chapter
19 ran the server with its synthetic source, which skips the link and the simulator's physics; the
reconstruction chapters read the simulator's files, which skip the server. Nothing ran the stages
as the scanner runs them, one after the other, and so nothing could show that what one stage
passes on is what the next stage receives.

Calling the result 1.0 also needs a statement of what 1.0 must show. Until now the release record
judged the performance requirements by reading the benchmark files ("read against SRS-PERF-020 and
SRS-PERF-021 by hand"), and nothing kept a requirement from being edited after it had been
verified.

## Options

1. **What the server's output is compared with.** Plausibility only (rates and spectra within
   chance of the simulator's, as Chapter 19's statistical golden test does); a stored golden file
   per configuration (Chapter 19's exact golden test, for the synthetic source); or an offline
   reference computed from the same singles by the simulator's own sorter, which must agree record
   for record.
2. **The singles the reference sorts.** The simulator's (double precision); or the singles as the
   link carries them, encoded as MDQ-P1 words and decoded again.
3. **How the stages are checked against each other.** Only the end products (the files and the
   image); or conservation equations between every pair of stages, from the counters each stage
   already reports.
4. **The acceptance decision.** Prose in the release record; the SDP's table of verifications; or
   a machine-readable specification of product-level criteria, each with its requirements, target
   and evidence file, evaluated by a tool that cannot turn missing evidence into a pass.
5. **Freezing the requirements.** A rule in the SDP; a tag of the SRS at the freeze; or a baseline
   of digests that a test compares with the SRS on every change, failing for each difference that
   no approved change request names.

## Decision

- **An offline reference of the same singles, quantized as on the link** (options 1 and 2, the
  last of each). `quantize_as_on_link` passes each single through MDQ-P1 and the server's own
  `StreamDecoder`; `minidaq_sim --link 1` sorts the result with the same `CoincidenceSorter` the
  server uses. Over a clean link the server must write exactly the reference's records
  (SRS-SYS-006). Without the quantization the two differ by design: 10 of 13,126 prompts in the
  first run, singles moved across the energy window's edges by the 0.5 keV rounding.
- **Conservation equations between the stages** (option 3, the second): sent and delivered,
  delivered and decoded, the sorter's partition of its singles and of its pair windows, the
  coincidences written, the records in the files and the records binned (SRS-SYS-007). Each
  equation uses counters the stages already had; the test shows that each counter off by one
  fails at least one equation. On a damaged link the records are not compared with the reference,
  because a lost single can also add a coincidence (a multiple that becomes a pair).
- **A machine-readable acceptance specification** (option 4, the third):
  `docs/regulatory/verification/acceptance.json`, evaluated by `tools/acceptance.py` from one
  output directory of the release checks. Its verdicts are PASS, FAIL, MISSING and STALE; only
  PASS counts. The SDP's table stays the list of verifications; the specification says what the
  product must show and where the evidence is.
- **A baseline of digests** (option 5, the third): `srs-baseline.json` and `tools/req_baseline.py`,
  in the test `docs.baseline`. The baseline is taken again only at a release, after the review of
  every difference.

## Consequences

### Positive

- The whole chain runs on every change (`system.e2e`, about 35 s in the debug build) and at every
  release with the image (`tools/e2e.py` in part 3). The first run found MDQ-PR-055, a count that
  disagreed between two programs and that no test of either program could see.
- Equality with the reference is a much stronger check than plausibility: a change that alters
  one record of a hundred thousand fails it.
- Missing or stale evidence can no longer pass a release unnoticed: evaluated against the evidence
  of release 0.7.0, the specification reports the end-to-end evidence as missing and the
  repository as stale (`measurements/ch33/acceptance-0.7.0.md`).
- A requirement cannot change silently after the freeze.

### Negative

- The reference is the simulator's sorter, which is also the server's: a defect in
  `CoincidenceSorter` is in both and the comparison cannot see it. The sorter's own tests, its
  truth-classified report (Chapter 10) and the statistical golden test cover that.
- The end-to-end run takes a minute and needs numpy and, for speed, the C++ projector; the test on
  every change leaves the image out.
- The acceptance targets are book-level numbers (assumption: confirm with team); a manufacturer's
  come from the scanner's system requirements.
- A baseline that is retaken carelessly freezes nothing: retaking it is part of the release
  review, not a way to make `docs.baseline` pass.
