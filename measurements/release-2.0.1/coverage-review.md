# Release 2.0.1 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage): every
branch and condition that the tests never took both ways on a line of a class B file changed since
release 2.0.0 (tag `book-v2.0.0`). The lines come from the `coverage` build of the release checks
(commit 620dc65), read by `tools/coverage.py --uncovered` (its function `gaps()`), restricted to
the lines that `git diff -U0 book-v2.0.0 620dc65` adds or changes in class B source. The totals
per software item are in `coverage.txt`.

## Lines changed since 2.0.0

Two class B sources changed, both for MDQ-PR-078 (the review of 2.0.0):

- `minidaq/src/control/listmode_sink.cpp` lines 603 to 615, the new
  `metadata_delayed_window_ps`.
- `minidaq/apps/minidaq_listmode.cpp` lines 199 to 201, which now call it.

## Finding

One, now tested:

- `listmode_sink.cpp:606`, the condition `!meta.contains("records")` was never true. The unit test
  `ListModeSink.ReadsTheDelayedWindowFromMetadataAsUntrustedInput` gave the reader every wrong
  type of `records` but no object without it. The test now adds `{}` and an object whose delay is
  under another key. Both are refused, as specified. The commit after 620dc65 changes this test
  only, and the programs are those of the checks. No defect was found.

The changed lines of `minidaq_listmode.cpp` have no untaken branch.

## Items whose branch coverage is lower than at 2.0.0

- `core` (85.1% to 83.8%, 2 of 154 branches): no source of the item changed since 2.0.0. Its
  untaken branches in this run include the tie-break of the flight recorder's merge
  (`flight_recorder.cpp` lines 40 and 43). That merge orders events of different threads by
  time, and only a tie between two threads' events in the same nanosecond takes it, which
  depends on the schedule of a run, not on the code.

Every other class B item has the same or a higher branch coverage than at 2.0.0.
