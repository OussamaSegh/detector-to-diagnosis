# Release 1.3.0 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage):
every branch and condition that the tests never took both ways on a line of a class B file
changed since release 1.2.0 (tag `book-v1.2.0`). The lines come from `tools/coverage.py
build/coverage OUT --no-run --uncovered FILE` on the `coverage` build of the release checks
(commit ced71e9), restricted to the lines that `git diff -U0 book-v1.2.0 ced71e9` adds or changes
in the 33 class B source files changed since 1.2.0 (`coverage-review-lines.txt`). The totals per software item are in
`coverage.txt`. Line numbers are those of ced71e9.

Each finding has one of three outcomes: tested (a test was added), infeasible (no input can take
the branch; the reason is given) or accepted (the branch is reachable, and the reason it may stay
untested is given). 55 lines were found in 15 files; the other 18 files have none.

## Items whose branch coverage is lower than at 1.2.0

`pipeline` (93.3% to 91.9%), `server` (73.8% to 66.9%), `service` (87.8% to 86.8%), `sorter`
(92.3% to 91.9%) and `update` (82.3% to 81.9%). Each is lower because new code added branches
that are classified below (the sort stage's marker, the server's two new options, the boards'
new fields in the status, the sorter's `advance`, and `update::verify_signature`, which now
forwards to `signing::verify`), not because a branch the tests took at 1.2.0 is no longer taken.
`server` is the program's command line and start-up, which the unit tests do not run.

## Tested

The tests below were added after the release checks (commit after ced71e9, tests only; the
programs are those of the checks). They found one defect, MDQ-PR-071.

- The check of a signed run (`minidaq/src/control/listmode_sink.cpp` lines 478 to 507, 523):
  `Signing.ASignedRecordThatDoesNotListItsFilesProperlyIsRefused` signs, with a trusted key,
  records without digests, with one digest too many, with a digest of another file, with a file
  that is not a name, with a path out of the run's directory, with a wrong size and with a file
  that is not there, and a signed text that is not JSON; and asks for a record that does not
  exist. Each is refused with its reason. Writing the test showed that a digest whose `sha256` or
  `bytes` has the wrong type ends the check with an exception instead of a refusal
  (MDQ-PR-071, open, to be fixed in 2.0.0-dev; it needs a malformed record signed by a trusted
  key).
- The decoder's marker (`minidaq/src/format/packed_single.cpp:51`, `packed_single.hpp:154`):
  `StreamDecoder.KeepsTheLatestOfSeveralMarkersAndNeverTakesTheMarkerForASingle`, a later
  marker after an earlier one in the same call, and a crystal count above the marker's crystal.

## Infeasible

- `minidaq/src/control/signing.cpp` lines 106 and 111: `EVP_PKEY_get_raw_public_key` of an
  Ed25519 key that `load` has just checked is Ed25519 returns 32 bytes, and SHA-256 of 32 bytes
  does not fail; the checks stay so that an OpenSSL error is a refusal, not undefined behavior.
- `signing.cpp` lines 123 to 125: signing with a loaded Ed25519 key fails only if OpenSSL cannot
  allocate; the signature of Ed25519 is always 64 bytes. With it, `listmode_sink.cpp:249` (the
  record not signed because signing failed) cannot be reached from a test either.

## Accepted

- **The programs' command lines** (`minidaq/apps/minidaq_server.cpp` lines 114, 116, 203, 205,
  212, 217; `minidaq_listmode.cpp` lines 270 to 306; `minidaq_send.cpp:87`): the new options
  `--signing-key`, `--calibration-keys`, `verify-run --keys` and `--marker-interval-us`. The
  unit tests do not run the programs; the functions behind each option are tested
  (`Signing.*`, `AcquisitionService` with a `calibration_verifier`, `TimeMarker.*`), and the
  options were run by hand on 2026-11-15: a run signed by the server with `--signing-key`
  verified by `minidaq_listmode verify-run` and by the analysis package, and refused after a
  byte of a data file changed. A system test of the signing options is to be added with
  2.0.0-dev's interface changes, which touch the same command lines.
- **Failed writes of the run record and its signature** (`listmode_sink.cpp` lines 244, 271,
  282 and 283): a short write, a failed `fsync` and a failed `close` of the record. The same
  `write_durably` path is the one the data files take, whose failures are tested through the
  file operations port; the record's own call
  differs only in the name in the fault message. Data-file failures are tested by
  `ListModeSink.ShortWritesAreCompleted` and `ListModeSink.AFullDiskIsAFaultAndTheFileStaysPart`
  (through the file operations port); the record's write is tested when it succeeds
  (`ListModeSink.StoresTheRunRecordNextToTheFiles`).
- **The status of boards with register map 1.1 or a malformed status** (`run_integrity.cpp`
  lines 72 to 87, `acquisition_service.cpp:56`): the combinations where the detector counters
  are missing or not numbers, a board list that is empty, or one board of an older map among
  newer ones. The status is written by the service itself, which always writes these fields
  together; `RunIntegrity.DatagramsTheBoardsSentButTheLinkNeverSawAreALoss` takes the outcomes
  that matter: a loss found, every datagram accounted for, and nothing compared with an older
  board. The individual conditions are defensive.
- **The default sink without a key, and other outputs with one** (`adapters.cpp` lines 57 and
  60): a service built with a sink of its own and a key, or a key with an output other than
  list mode. The tests pass a key with list mode and no key at all; the other combinations
  select the default sink unchanged from 1.2.0.
- **Register map 1.2 on boards of firmware 2.x, and failed writes of the marker registers**
  (`slow_control.cpp` lines 228, 231, 259; `fake_board.cpp:223`): no firmware 2 exists; a
  failed write of the marker interval and a failed read of the datagrams sent take the same
  `failed_cycle` path as the other registers, which `SlowControl.AFailedWriteIsAFailedAccessAndNeverEnablesTheBiasEarly`
  tests for the bias.
- **The sort stage's marker in its rarer combinations** (`acquisition_pipeline.cpp` lines 270,
  290 and 292): a flush with no single held and no marker, and a marker that arrives while more
  than a batch of singles is held. `Pipeline.AMarkerDeliversTheLastCoincidencesWhileTheSourceIsSilent`,
  `Pipeline.MarkersChangeNoCoincidence` and `CoincidenceSorter.MarkersChangeNoCoincidence` verify that a marker releases every single
  before it and never changes a coincidence; the combinations are reachable only at rates where
  a batch fills between two markers, which the soak (1 M singles/s, markers off) does not reach.
- **The sorter's `advance` with a marker no later than the last time** (`coincidence_sorter.cpp`
  line 140, the condition `have_last_` alone): a marker before any single; harmless, the
  function then only records the time.
- **The simulated link's marker schedule** (`readout_link.cpp` lines 44 and 52): an interval of
  zero (markers off) with an end time, and a stream with no single; simulation code, class B
  because it is linked into the server (MDQ-PR-009).
