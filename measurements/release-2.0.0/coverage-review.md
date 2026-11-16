# Release 2.0.0 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage):
every branch and condition that the tests never took both ways on a line of a class B file
changed since release 1.3.0 (tag `book-v1.3.0`). The lines come from the `coverage` build of the
release checks (commit c977dd9): `llvm-cov show` with the profiles of that run, read by
`gaps()` of `tools/coverage.py` (the function behind `--uncovered`), and restricted to the lines
that `git diff -U0 book-v1.3.0 c977dd9` adds or changes in the 28 class B source files changed
since 1.3.0 (`coverage-review-lines.txt`). The totals per software item are in `coverage.txt`.
Line numbers are those of c977dd9.

Each finding has one of three outcomes: tested (a test was added), infeasible (no input can take
the branch; the reason is given) or accepted (the branch is reachable, and the reason it may stay
untested is given). 23 lines were found in 9 files; the other 19 files have none.

## Items whose branch coverage is lower than at 1.3.0

- `config` (80.6% to 79.6%): schema 2.0 and 2.1 (CR-0030, CR-0031) added 26 branches, 18 of
  them taken. On the changed lines the only untaken branch is the defaulted equality of the new
  `TimingMonitorSettings` (below); each settings structure's defaulted `operator==` has a false
  branch that only a comparison of two different configurations takes.
- `hw` (89.4% to 88.3%): the item is smaller, not less tested. CR-0029 moved the simulated
  board (`fake_board`) out of the shipped items into `sim`, which is not shipped, so `hw` lost
  136 branches, most of them taken. The new branches of the clock status (CR-0031) are tested
  below.
- `rt` (77.1% to 76.2%): no source of the item changed since 1.3.0. The two branches not taken
  this time are refusals by the machine: in this run every request for a real-time scheduler
  was granted (`realtime.cpp` line 130 never false, line 132 never reached), so the path that
  records a refusal was not taken. Which requests a machine grants depends on its privileges,
  not on the code.

Every other class B item has the same or a higher branch coverage than at 1.3.0; `server`
rose from 66.9% to 83.1% with the branch tests of 2.0.0-dev.

## Tested

The tests below were added after the release checks (a commit after c977dd9 that changes tests
only; the programs are those of the checks). They found no defect.

- The time base monitor (`minidaq/src/processing/timing_monitor.cpp`):
  `BlockOffsets.PairsThatCannotBeUsedAreLeftOut` gives the solver pairs with a variance that is
  zero or not a number, a block paired with itself and a block beyond the scanner's (lines 72
  and 157); `TimingMonitor.NamesEachLevel` names the four levels (lines 37 and 42);
  `TimingMonitor.IgnoresCoincidencesWithinOneBlockOrOfACrystalThatDoesNotExist` records a
  scan with such coincidences mixed in and finds the same pairs and offsets as without them
  (lines 219 and 224); and `TimingMonitor.RefusesAConfigurationThatCannotWork` now also refuses
  a negative delay (line 30).
- The API version (`minidaq/src/control/control_protocol.cpp:164`):
  `ControlProtocol.VersioningAndMalformedInput` now sends a request without `"api"`, which 3.0
  refuses (SRS-CTL-022, amended by CR-0030). No test sent such a request before: the test had
  every other case, and its helper `call()` adds the version to a request that has none. The
  refusal works as specified; CR-0030's verification lacked this one case.
- The check of a signed run (`minidaq/src/control/listmode_sink.cpp` lines 503 and 512):
  `Signing.ASignedRecordThatDoesNotListItsFilesProperlyIsRefused` adds a digest that is not
  an object, a digest without its file and a digest without its size. Each is refused with its
  reason.
- The clock status (`minidaq/src/hw/slow_control.cpp:274`):
  `SlowControl.ReadsEachBoardsClockAndStartsNoRunWithoutALock` adds a board whose clock
  status cannot be read: a failed access, and a fault after three, as for any other register.

## Infeasible

- `slow_control.cpp:272`, `major > 1`: a board of another major version than the settings'
  `firmware_major` is refused before this line (SRS-HW-011), and the shipped settings name
  major 1. The condition is written for the map of a later major version, so that a new
  `firmware_major` does not silently lose the clock status.
- `minidaq/include/minidaq/config/acquisition_config.hpp:121`, the false branch of a defaulted
  `operator==`: no program compares two configurations; the tests compare a configuration
  with its own round trip through JSON, which is equal by design. Taking the branch tests the
  compiler, not MiniDAQ.

## Accepted

- **The programs' command line** (`minidaq/apps/minidaq_ctl.cpp:269`): `minidaq_ctl wait`
  ends with an error when the connection fails between two status requests. The unit tests do
  not run the program; the system tests run `wait` against a server that stays up. The error
  path prints the connection's error and returns 2, as every other command's does.
- **The product build's refusal** (`minidaq/src/control/acquisition_service.cpp:169`): the
  coverage build has the simulator, so the refusal of a synthetic source never runs there. It
  is tested in the `product` build, which the release checks build and test in part 1:
  `Product.test_the_product_refuses_simulated_boards_at_start_up` and the unit tests of the
  product preset (CR-0029).
- **The boards' datagram count in the status** (`acquisition_service.cpp:58`): a board reports
  the datagrams it sent only while its triggers are on with register map 1.2; the service's
  tests read the boards' status outside a run. The slow control's reading is tested
  (`SlowControl.SwitchesTheTimeMarkersOnWithTheTriggersAndReadsTheDatagramsSent`), and so is
  its use in the integrity verdict
  (`RunIntegrity.DatagramsTheBoardsSentButTheLinkNeverSawAreALoss`); this line copies the
  value into the status.
- **A message's grammar** (`acquisition_service.cpp:475`): the audit event of a clock that lost
  its lock says "1 time" or "N times"; the tests lose the lock once. The event and its count
  are tested; the plural is wording.
- **A status written by the service itself** (`minidaq/src/control/run_integrity.cpp:48`):
  `sorter_counters` that is not an object is skipped, as `timing` and `sink_counters` are. The
  service always writes it as an object; the verdict reads a status the same server made.
- **The update store's optional versions** (`minidaq/src/update/slots.cpp` lines 328 and 334):
  a `state.json` without `good_version` or `trial_version`. Every release since 0.5.0 writes
  both fields, so such a state was not written by MiniDAQ. It opens with an empty version, as it
  did before MDQ-PR-074's fix (`value(..., "")`). With no installed version, the next install
  is not compared with it for a downgrade (`slots.cpp:402`); the bundle must still carry a
  valid signature from a trusted key, and the state is writable by root only (threat T-44).
  Kept as it is: a store that lost its versions can still be updated. `Update.OpenRefusesAStoreItCannotTrust` checks that a
  field of another type is refused (MDQ-PR-074).
