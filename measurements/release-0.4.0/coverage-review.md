# Release 0.4.0 structural coverage review

The review that the development plan asks of a release: every branch that the debug tests never
took on a line of a class B file changed since release 0.3.0 (commit `57ef123`). The branches
come from `tools/coverage.py BUILD OUT --no-run --uncovered` on the `coverage` build of the
released code, restricted to the changed lines of the 18 class B files changed since 0.3.0. The
totals per software item are in `coverage.txt`.

Each finding has one of three outcomes: tested (a test was added), infeasible (no input can take
the branch; the reason is given) or accepted (the branch is reachable, and the reason it may stay
untested is given).

## Tested

- `minidaq/src/control/udp_detector.cpp:168`, the flight-recorder event for a link
  resynchronization: no test made a board renumber its packets. Added
  `UdpDetector.TracesAResynchronizationOfTheLink` (SRS-DIAG-004), which fails when the trace is
  removed (checked by hand on 2026-10-26).

## Infeasible

- `minidaq/include/minidaq/format/readout_packet.hpp:246`, `overtaken` true when the gap closed
  while making room: `overtaken` means a later packet arrived first, which leaves `highest_` ahead
  of `next_` inside the window, and making room only happens when `seq` lies beyond the window.
  Both cannot hold for one packet. The header is not changed for this release, since Exercise
  18.5 records its SHA-256.
- `minidaq/src/control/acquisition_service.cpp:253`, a fault of source `other`: every caller of
  `enter_fault_locked` prefixes its reason with `detector:`, `sink:` or `sort:` (lines 278 to
  300), so the last arm of the choice is never reached. It stays so that a new caller without a
  prefix is still traced.
- `minidaq/src/control/control_protocol.cpp:93`, a response without a boolean `ok`: the function
  only sees responses that the server built itself, and each has one. The check keeps the trace
  right if a response were ever built without it.

## Accepted

- The crash report (`minidaq/src/rt/crash_report.cpp`, 13 lines, and the `--crash-report` path
  of `minidaq/apps/minidaq_server.cpp`, lines 83 to 115). A process that dies of a signal never
  writes its coverage profile, so the paths that run in the dying process show as untaken. They
  are verified by `CrashReportDeathTest` (a fault and an abort each write the report, and the
  process still dies of the signal) and by the system test
  `test_a_crashed_server_leaves_a_report_and_dies_of_the_signal`. The rest are error paths of
  system calls that a test cannot make fail without a fault injector: `write` interrupted or
  failing (lines 79 to 94), and `sigaltstack` and `sigaction` failing (lines 237 and 245). On
  each, the code gives up writing and the process still dies of its signal, which is the safe
  outcome; the crash report is a diagnostic, not a risk control.
- `minidaq/apps/minidaq_ctl.cpp:303`, `minidaq_ctl diagnostics` without a number of events:
  the request then has no count and the server answers with its default. The tool's tests always
  give the number; the server's default is tested by `ControlProtocol` tests of `diagnostics`.
- `minidaq/src/core/flight_recorder.cpp:10`, the switch that names a trace code with a value
  that is none of its cases: every named code is tested (`test_flight_recorder.cpp`, lines 184
  to 192), and a value outside the enumeration, which only a corrupted event could hold, is named
  `none`.
- `minidaq/src/core/flight_recorder.cpp:40`, two events of the same ring with the same time in
  nanoseconds: the order then falls back to the sequence number within the ring. A thread writes
  one ring, and two of its events in the same nanosecond did not occur in the tests; the order is
  still total.

## Totals

Branch coverage of the two class B items with the most new code fell since Chapter 19: `rt` from
74.6% to 74.2% and `server` from 81.1% to 75.0%. Both falls are the crash report's code above,
which runs in processes that do not write their profile. Every class B item still covers at least
75% of its lines (`coverage.txt`).
