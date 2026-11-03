# Release 0.6.0 structural coverage review

The review that the development plan asks of a release: every branch and condition that the
debug tests never took on a line of a class B file changed since release 0.5.0 (tag
`book-v0.5.0`). They come from `tools/coverage.py BUILD OUT --no-run --uncovered` on the
`coverage` build, restricted to the changed lines of the 11 class B source files changed since
0.5.0. The totals per software item are in `coverage.txt`.

Each finding has one of three outcomes: tested (a test was added), infeasible (no input can take
the branch; the reason is given) or accepted (the branch is reachable, and the reason it may stay
untested is given). Line numbers are those of the checked commit 893413d; the commits after it
changed only tests and documents, so they are also those of the release.

## Tested

The first pass of this review, on commit 893413d, found 42 lines with an untaken branch or
condition. The tests below were added for them (commits ef85887 and 7fa5b1d) and the review was
made again on a9c5ba7, which has the same programs and the new tests (`coverage-a9c5ba7.txt`,
`coverage-review-gaps.txt`): it leaves the 26 lines classified below.

- The calibration table's timestamps and temperature (`minidaq/src/processing/calibration.cpp`
  lines 63, 117, 149 to 160 and 168): each separator wrong in turn, a non-digit in each field,
  above `9` and below `0`, 28 February of a year that is not a leap year, and a reference
  temperature below -40 C (`Calibration.KnowsAUtcTimestampWhenItSeesOne`,
  `Calibration.RefusesATableThatDoesNotSayWhereAndWhenItWasMade`).
- The calibration file's forms (`minidaq/src/config/calibration_file.cpp` lines 62, 98 and 145):
  a time offset below the 32-bit range, a `schema_version` that is not a string, and a `time`
  that is not an object (`CalibrationFile.RefusesEachMalformedPart`).
- A profile file larger than 64 KiB (`minidaq/src/control/acquisition_service.cpp:80`):
  `AcquisitionService.ProfilePathMustBeASmallRegularFile`.
- A batch of singles that holds only unknown crystals
  (`minidaq/src/processing/singles_counter.cpp:43`):
  `SinglesCounter.ABatchOfOnlyUnknownCrystalsChangesNothing`.
- A delay spread without a gain spread (`minidaq/src/sim/detector_simulator.cpp:99`):
  `DetectorSimulator.ADelaySpreadAloneLeavesEveryGainAtOne`, which also shows that the delays of
  a seed do not depend on the gain spread.
- An empty decoded batch and the identity calibration table in the pipeline
  (`minidaq/src/pipeline/acquisition_pipeline.cpp` lines 183, 240 and 245):
  `Pipeline.ABatchWithoutValidWordsAndAnIdentityTableChangeNothing`. Without the guard of line
  245 an empty batch would read `v.back()` of an empty span; the test runs under the sanitizers
  in the `asan-ubsan` preset.

These tests found no defect.

## Infeasible

- `calibration_file.cpp:54`, `std::isfinite(d)` false: JSON text has no NaN or infinity, and
  the parser refuses a number beyond the range of a double (`1e400` gives
  `json.exception.out_of_range.406`), so every number that reaches the check is finite. The
  second condition, a finite value beyond the range of a float, is tested (`1e39`). The check
  stays so that the function is correct for any `json` value, not only a parsed one.

## Accepted

- **The simulator's command line** (`minidaq/apps/minidaq_sim.cpp` lines 102, 106, 305 to 339
  and 479 to 493): the options of the uncalibrated detector, the source's radius and length, the
  crystal truth file and the truth sinograms. The unit tests do not run the program; the
  measurements of Chapters 26 to 30 do, with each of these options (`measurements/ch26/` to
  `measurements/ch30/`), and their results are the evidence of SRS-CAL, SRS-COR, SRS-REC and
  SRS-IQ. Lines 121 to 126 and 482 to 487 are failed writes of the output files: each makes the
  program exit with a non-zero status, which the measurement scripts check.
- `acquisition_service.cpp:96`, a profile file that grew between `fstat` and `read`: it takes a
  second process writing the file during the read. The read stops at the limit plus one byte, so
  such a file is refused and never read beyond the buffer; the refusal is the same message as
  that of line 80, which is tested.
- `acquisition_pipeline.cpp:264`, more held singles than one batch: it needs a calibration whose
  time spread is longer than the time one batch of singles covers. The table allows offsets of
  at most 5 ns either way, a spread of at most 10 ns, so a batch of 512 singles would have to
  arrive within 10 ns, a rate of 5 x 10^10 singles per second, far above what the scanner's
  detector produces. The guard keeps the stage's memory within the two batches it reserves
  before it counts as started, so that it never allocates while it runs; the singles it would
  send early are counted by the late counter (SRS-CAL-003), which the tests check.

## Totals

26 lines in 4 files: 0 left open, 1 infeasible, 25 accepted with their reasons (23 of them in
the simulator's command line). Before the tests of this review, 42 lines.

Every class B item covers at least 75% of its lines (`coverage-a9c5ba7.txt`), and no item's branch
coverage is lower than at 0.5.0. Part VI's items gained: `processing` from 78.1% to 89.7% of its
branches, `pipeline` from 90.1% to 93.3% and `config` from 75.7% to 80.6%. The run on 893413d
(`coverage.txt`) gave `core` and `protocol` 1.3 and 0.3 points fewer branches than the run on
a9c5ba7, and `rt` and `hw` 0.5 and 0.3 points more, for the same code: branches taken by threads
depend on their timing from run to run, which is why the comparison with 0.5.0 uses the later run
and the review lists only changed lines.
