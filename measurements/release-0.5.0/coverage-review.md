# Release 0.5.0 structural coverage review

The review that the development plan asks of a release: every branch and condition that the
debug tests never took on a line of a class B file changed since release 0.4.0 (tag
`book-v0.4.0`). They come from `tools/coverage.py BUILD OUT --no-run --uncovered` on the
`coverage` build of the released commit 6ef606e, restricted to the changed lines of the 38 class
B files changed since 0.4.0. The totals per software item are in `coverage.txt`.

Each finding has one of three outcomes: tested (a test was added), infeasible (no input can take
the branch; the reason is given) or accepted (the branch is reachable, and the reason it may stay
untested is given). Line numbers are those of the released commit.

## Tested

The first pass of this review, on commit 0c5c2e8, found 152 lines with an untaken branch or
condition. The tests below were added for them (commits 6730ae2, d5f3e09 and 6ef606e) and the
review was made again on the released commit, which leaves the 144 lines classified below.

- The updater's refusals (`minidaq/src/update/bundle.cpp`, `slots.cpp`): a manifest that is not
  an object, has fields of the wrong type, a wrong size, version or digest length, or an empty
  archive; a key directory without keys or with a file that is not a key; a bundle for another
  product, an archive changed without changing its size, an archive that `tar` cannot list, a
  missing archive; a manifest that names a file twice or outside the tree; a store that cannot be
  trusted (`test_update.cpp`, among them `RefusesABundleForAnotherProductOrWithoutItsArchive`,
  `UpdateTree.AManifestNamesEachFileOnceAndInsideTheTree` and `OpenRefusesAStoreItCannotTrust`).
- The board's own protection findings and refused writes (`minidaq/src/hw/slow_control.cpp`):
  `LatchesTheBoardsOwnOvertemperatureAndOvercurrentFindings` and
  `AFailedWriteIsAFailedAccessAndNeverEnablesTheBiasEarly`.
- The hardware description's ranges (`minidaq/src/config/hardware_config.cpp`):
  `HardwareConfig.RefusesEachFieldOutsideItsRangeOnItsOwn`, and an empty `schema_version` in
  `test_config.cpp`.

These tests found three defects, corrected before the release checks: an empty `schema_version`
was accepted (MDQ-PR-042), a board's overcurrent trip was reported as a measured current
(MDQ-PR-043), and a board that refused every write never latched a fault (MDQ-PR-044).

## Infeasible

- `minidaq/src/update/slots.cpp:174`, `path.empty()` true: `contained(path)`, the first
  condition, refuses an empty path, so the second is never reached with one. It stays so that
  the line reads as the full list of names a manifest may not hold.
- `minidaq/src/control/acquisition_service.cpp:319`, a fault of source `other`: every caller of
  `enter_fault_locked` prefixes its reason with `detector:`, `sink:`, `sort:` or, new in Part V,
  `hw:`, so the last arm is never reached, as found at 0.4.0 for the same line.

## Accepted

- **Failures of system calls and of OpenSSL**: `slots.cpp` lines 48 to 128 (open,
  fsync, write, rename and the directory's fsync of an atomic write; pipe, fork, read and waitpid
  of the `tar` child), 182, 199, 204, 268, 281 to 288, 303, 343, 356, 409, 425 (`tar` that lists
  an archive and then fails to extract it), 448 to 497 (a failed write of the state or switch of
  the link in install, confirm and rollback); `bundle.cpp` lines 161 to 222 (reading a file,
  OpenSSL contexts and digests); `mmio_bus.cpp` lines 29 to 67 (open and mmap of the device);
  `service_manager.cpp` 33, 72 and 79 (the notification socket); `udp_detector.cpp` 34 to 58 and
  106 (getifaddrs, the kernel's overflow message, fstat). None can be made to fail without a
  fault injector. Each returns an error that the caller reports, and the updater's writes are
  atomic (write a temporary file, fsync, rename, fsync the directory), so a failure leaves the
  previous state and the previous version in use, which is the safe outcome of H-05. The paths
  that matter most, a power cut between the steps of an install, are tested by
  `Update.APowerCutAfterAnyStepLeavesAVersionThatRuns`, which cuts the install after each step.
- **The command-line tools**: `minidaq/apps/minidaq_update.cpp` (usage errors, an
  option without its value, an option given to the wrong command, a store that cannot be opened)
  and `minidaq/apps/minidaq_server.cpp` lines 102 to 205 (the `--hardware` option without a value
  and start-up errors with a hardware description that cannot be read or a port that cannot be
  opened). Each prints its reason and exits with a non-zero status before any acquisition; the
  normal paths are tested by the system tests (34 cases). Lines 259 to 269 of the server, the
  watchdog's answer when the hardware's heartbeat stops, are verified by the unit tests of
  `rt::Health` and the slow control's hung-bus tests, and the system test
  `test_a_loop_that_hangs_stops_the_pings_and_says_why` covers a hung loop, but no system test
  stops the hardware's heartbeat; a system test of the
  watchdog on a hung bus is planned for the next release (problem: none, a gap in verification
  depth, recorded in HANDOFF.md).
- **The simulated board** (8 lines, `minidaq/src/hw/fake_board.cpp`): combinations of injected
  faults and register addresses that no test needs, in the simulator that the tests and the
  demonstration use. It is linked into the server (MDQ-PR-009) but never drives real hardware.
- **Diagnostics that control no risk**: `minidaq/src/net/host_counters.cpp` (parsing
  of `/proc/net` files with missing or malformed fields, counters that went back, interface names
  refused for the path) and `minidaq/src/control/hardware.cpp` lines 24 to 48 and 86 to 87 (the
  names of the simulated faults given on the command line, the `mmio` backend, which needs a
  device, and a temperature file that cannot be read). The host counters only explain a loss
  after the fact; the loss itself is counted by the pipeline.
- **Names for messages**: the switches that name an error code, a board state or a
  temperature level (`register.cpp` lines 7 to 14, `slow_control.cpp` lines 17 to 34) and the
  hint for an identity of all ones (`slow_control.cpp:144`). Every value that the tests produce
  is named; the remaining arms only change a message.
- **Defensive guards and combinations of conditions**:
  - `slow_control.cpp:80`, a latch on a board already in fault: each caller latches at most once
    per cycle and stops at its first fault, so the guard only keeps the first cause should a
    later change call it twice;
  - `slow_control.cpp:222`, 251, 355 and 363: a FIFO overflow while triggers are on but the board
    has not switched yet; a failed ramp-rate write of a board that is not configured (the write
    of the setpoint after it is tested); `triggers_are` and `drained` before the first cycle,
    which the service never asks;
  - `minidaq/include/minidaq/hw/register.hpp:44` (the defaulted comparison of two different
    errors) and 152 (`write_field` when its read fails; the tests fail writes, not the read of
    a read-modify-write);
  - `acquisition_service.cpp` lines 283, 310, 363, 372 and 387: a reset with hardware from a
    state other than fault, and the trigger and drain timeouts and snapshots when no hardware is
    configured; each combination is the normal path of the other configuration;
  - `minidaq/src/control/run_integrity.cpp:59`: a status with hardware but no list of boards,
    which the server never writes;
  - `minidaq/src/rt/health.cpp:21`, `minidaq/src/control/service_manager.cpp` 29, 54, 56 and
    131, and `udp_detector.cpp:30`: environment variables and addresses in forms that the
    service manager does not produce;
  - `slots.cpp:230` and 231, a store moved onto itself.
- **Configuration forms**: `hardware_config.cpp` lines 77 and 79 (a description that
  is not an object, a version that is not a string) and `minidaq/src/config/object_reader.hpp`
  lines 44, 46, 179 and 180 (keys holding `~` or `/` in an error's JSON pointer, the separate
  conditions of a malformed version). The same checks are tested in the acquisition
  configuration, which shares the reader; the hardware description's own tests of these forms
  will be added in the next release with the other configuration of Part VI.
- `slots.cpp:392`, an install when the state has no good version: only a state file edited by
  hand has none, and `open()` refuses a state it cannot read. The downgrade check then lets the
  install go on, which is the behavior of a first install; a test would need a state file that
  the updater never writes.

## Totals

144 lines in 18 files: 0 left open, 2 infeasible, 142 accepted with their reasons (the groups
above). Before the tests of this review, 152 lines.

Every class B item covers at least 75% of its lines (`coverage.txt`); the new items of Part V
cover `hw` 94.8%, `platform` 96.2% and `update` 85.1% of their lines. Branch coverage fell only
for `server`, from 75.0% to 73.8%, by its start-up and watchdog lines above.
