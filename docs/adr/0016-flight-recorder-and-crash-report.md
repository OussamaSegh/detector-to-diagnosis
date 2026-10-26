# 0016. A flight recorder in memory and a crash report written by the dying process

Date: 2026-10-26
Status: Accepted

## Context

Chapter 21 asks what MiniDAQ can tell you about a failure after the fact. Until now the answer
was the audit trail (who commanded what, Chapter 15), the status (counters at the moment you ask)
and the server's standard error. None of them says what the server did in the seconds before a
fault, and none of them survives a crash with anything useful: a segmentation fault ends the
process without a word, and output still in a stdio buffer is lost with it.

Three questions come up in every incident review of a data acquisition: what happened just
before, which build was running, and where exactly it died. The answers must be there the first
time the failure happens, because a fault that takes a week of acquisition to reproduce cannot
be debugged by restarting the server with more logging. And whatever records them runs in the
class B server process (software item list, items core and rt), so it must not slow the
pipeline or add a way to fail.

## Options

1. **More logging.** Log every state change, command and link loss to a file, with levels.
   Simple and familiar. But a log written to disk costs a system call or a lock per line on the
   threads that write, it is off at the level where it would have helped, and the last lines
   before a crash are the ones still in a buffer.
2. **A crash-reporting library** such as Google's Breakpad or Crashpad, which write a minidump
   from a separate process. Proven and complete, but large new SOUP in the server process
   (SOUP list), built and reviewed by the project, and a minidump needs its own tools to read.
3. **Core dumps only**, kept by the system (`systemd-coredump` or a `core_pattern`). No code in
   MiniDAQ at all. A core holds the whole memory and every thread's stack, but only where the
   system is set up to keep them, and it does not say what led to the state it shows.
4. **A flight recorder and a crash report of MiniDAQ's own, plus core dumps.** An in-memory ring
   of the last events of each thread, always on; a signal handler that writes a short text
   report (signal, address, version, build ID, the recorder's last events) with
   async-signal-safe calls only, then dies of the same signal so that the core dump is still
   made; and a control command, `diagnostics`, that returns the recorder's events from a server
   that is still running.

## Decision

Option 4.

- The flight recorder (`minidaq/core/flight_recorder.hpp`) gives each recording thread a ring of
  256 events, 32 rings in all, in static memory. A thread writes only its own ring, so a record
  is a few atomic stores without a lock or a read-modify-write; each slot is a seqlock, so a
  snapshot copies only complete events. Measured: about 33 ns per event on the reference
  machine, of which about 28 ns is the clock (`measurements/ch21/bm_flight_recorder.txt`).
- What is recorded: state changes, every control command with its outcome, the begin and end
  of each run, faults with their source, and the readout link's losses and resynchronizations.
  Not the data path: nothing per single, per batch or per packet.
- The crash report (`minidaq/rt/crash_report.hpp`) is installed first in `main`, writes to
  standard error or to the file of `--crash-report`, and re-raises the signal with its default
  action. `tools/postmortem.sh` opens the core with the program and its debug information
  (Chapter 20) and checks that their build IDs match.
- `diagnostics` (control API 2.1) needs the observer role, like `status`: the events hold numbers
  only (codes, run numbers, counts), no identities or tokens.

## Consequences

### Positive

- The last events before a fault are there the first time it happens, in a running server
  (`minidaq_ctl diagnostics`) and in the report of a crashed one.
- The report names the exact build, so the right debug information opens the core, and a report
  from a build that was never released is recognized as such.
- No new SOUP; the code is about 600 lines with comments, reviewed and tested with the rest (death tests for
  the report, a concurrency test under ThreadSanitizer for the recorder).

### Negative

- 256 events per thread is a few seconds of control activity, not hours: the recorder answers
  "what just happened", the audit trail answers "who did what", and they do not replace each
  other.
- The alternate signal stack serves the thread that installed the handler. A stack overflow in
  another thread ends the process with a core dump but without a report.
- A crash handler runs in a process whose memory may already be corrupt. The handler reads only
  static memory and the recorder's atomics, but a corruption that hit those can garble the
  report; the core dump is the evidence of record.
- A core dump holds everything in memory, including tokens and patient-related data if the
  product handled any (assumption: confirm with team how cores are kept and who may read them).
