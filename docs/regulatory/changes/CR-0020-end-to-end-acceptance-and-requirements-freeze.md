# CR-0020: The chain end to end, the 1.0 acceptance specification and the requirements freeze

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: the capstone of MiniDAQ 1.0 (Chapter 33); problem report MDQ-PR-055 |
| Decision | approved, 2026-11-04, software lead |
| Commits | 392e4ae, 78800d4 |

## Description

Four changes that together let MiniDAQ be accepted as a whole, not stage by stage:

1. **The readout link model** `minidaq::sim::quantize_as_on_link` gives each single what the server
   decodes from its MDQ-P1 word (5 ps, 0.5 keV, across the time counter's wraps), and
   `minidaq_sim --link 1` applies it before the sorter. With it, the offline sorter of the
   simulator and the server, given the same singles over a clean link, write identical records.
2. **The end-to-end run** `tools/e2e.py` (TL-40) runs two acquisitions through the shipped
   programs (a point source for the daily QC, a water phantom for an image), compares the server's
   records with the offline reference, checks that every count balances between the stages, runs
   the QC report of Chapter 31 and reconstructs the phantom by OSEM. The release checks run it in
   part 3; the test `system.e2e` runs a short version on every change.
3. **The acceptance specification** `docs/regulatory/verification/acceptance.json`: nine criteria,
   ACC-01 to ACC-09, each with its requirements, its target and its evidence file;
   `tools/acceptance.py` (TL-41) gives each a verdict (PASS, FAIL, MISSING or STALE) from one
   output directory of the release checks. `tools/release_checks.sh` also writes every result into
   `release-checks.txt`, which used to be collated by hand.
4. **The requirements freeze** `docs/regulatory/srs-baseline.json`, a digest of every requirement
   of SRS version 21 (release 0.7.0); `tools/req_baseline.py` (TL-42, test `docs.baseline`)
   fails for every requirement added, changed or removed since that no approved or implemented
   change request names.

And the fix of MDQ-PR-055: `minidaq_sim` prints as recorded the singles it uses, not those it had
simulated past the end.

## Reason

Every stage of MiniDAQ is tested on its own, and the system tests of Chapter 19 run the server with
a synthetic source. Nothing ran the detector simulator, the readout link, the server, the list
mode, the sinograms, the corrections, the reconstruction and the QC report as one chain, and so
nothing could show that a count leaving one stage is the count the next stage received. The first
end-to-end run found a mismatch at once (MDQ-PR-055). Without a written acceptance specification,
the release record's judgement of the performance requirements was made by hand ("read against
SRS-PERF-020 and SRS-PERF-021 by hand"), and nothing stopped a requirement from changing in an edit
after it had been verified.

## Impact analysis

### Requirements

Added (SRS version 22): SRS-SIM-024 (the readout link model), SRS-SYS-006 (the server's records
equal the offline reference's over a clean link), SRS-SYS-007 (the counts balance between the
stages), SRS-SYS-008 (the image of the end-to-end phantom, by demonstration), and SRS-PERF-022
(the end-to-end latency at 1 M singles/s, measured by the soak since Chapter 19 and stated by no
requirement until now). None changed or withdrawn. These five are the differences from the
baseline that this request names.

### Software items and safety class

The item `sim` gains `quantize_as_on_link` and the option `--link`; `minidaq_sim`'s summary line
changes (MDQ-PR-055). No item of the acquisition path (readout, pipeline, sorter, output, service)
changes; no class changes. The new tools are tools (TL-40 to TL-42), not items of the product.

### Risk

No hazard and no estimate changes. The end-to-end comparison adds verification to the controls of
silent data loss (H-01: RC-01 to RC-03, the counters and the integrity verdict) at the level of
the whole chain: a count that one stage loses or invents fails SRS-SYS-007 even when every stage's
own tests pass. The acceptance specification adds no control; it makes the release decision's
evidence explicit (SDP section 8).

### SOUP

None added or upgraded. The end-to-end run uses numpy, as the reconstruction tool already does.

### Interfaces and data formats

`minidaq_sim` gains the option `--link 0|1` (default 0, the previous behavior) and the field
`simulation.link` in its run record. The control protocol, the configuration schema, MDQ-R1,
MDQ-P1 and MDQ-L1 do not change. New files: the end-to-end result `e2e.json` (format "MiniDAQ
end-to-end result", version 1), the acceptance specification and the requirements baseline.

### Documents

The SRS, version 22; the development plan, version 12 (section 6: the end-to-end run; section 8:
the acceptance report); the tool list (TL-40 to TL-42) and `tools.md`; the threat model, version
8 (review: no new element of the running system); ADR 0028; the problem report MDQ-PR-055; the
trace matrix; the CHANGELOG.

### Regulatory

The intended use of MiniDAQ does not change. A real manufacturer's acceptance criteria come from
the scanner's system requirements and its design validation, not from a software team's choice
(assumption: confirm with team).

## Verification

The tests QuantizeAsOnLink.TruncatesTimeTo5PsAndRoundsEnergyToHalfKeVKeepingTheTruth,
QuantizeAsOnLink.GivesWhatTheServersDecoderGivesAcrossTheTimeWrap and
QuantizeAsOnLink.RefusesACrystalOutsideTheScanner; system.e2e (among them
EndToEnd.test_a_clean_link_gives_the_reference_records_and_every_count_adds_up,
EndToEnd.test_a_damaged_link_gives_an_incomplete_run_with_every_packet_accounted_for and
Accounting.test_every_counter_off_by_one_fails_a_check); tools.acceptance; tools.req_baseline;
docs.baseline; tools.release_checks; the whole ctest. `tools/e2e.py` on the release build
(`measurements/ch33/`) and `tools/acceptance.py` against the evidence of release 0.7.0.

## Decision

Approved on 2026-11-04 by the software lead: a release is accepted on the evidence of the whole
chain against a written specification, and a frozen requirement changes only through change
control.
