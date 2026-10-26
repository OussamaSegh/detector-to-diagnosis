# CR-0007: A flight recorder, a crash report and the diagnostics command (API 2.1)

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-10-26, by the software lead |
| Source | improvement: problem reports MDQ-PR-019 to MDQ-PR-023 were each diagnosed from evidence gathered after the fact, by reproducing the failure; development plan section 9 (problem resolution needs the data to analyze a problem) |
| Decision | approved, 2026-10-26, software lead and risk manager |
| Commits | none yet |

## Description

The server keeps the last events of each of its threads in memory (the flight recorder): state
changes, control commands with their outcome, the begin and end of each run, faults, and the
readout link's losses and resynchronizations. A new control command, `diagnostics`, returns the
newest events with the program's version and build ID, for an observer. When the server dies of
a fatal signal it writes a crash report with the same information to standard error or to the
file of a new option, `--crash-report`, and then dies of the same signal, so that a core dump is
still made. A new tool, `tools/postmortem.sh`, opens a core dump with the program and its debug
information and checks that their build IDs match. Problem reports gain an optional root-cause
field.

## Reason

A fault in the field must be diagnosable the first time it happens. Today a crash leaves no
trace in MiniDAQ's own output, the status shows only the counters at the moment it is read, and
the audit trail records commands but not what the server did between them. Without the change
the team reproduces each failure before it can analyze it, which for a fault after hours of
acquisition means days.

## Impact analysis

### Requirements

New: SRS-DIAG-001 to SRS-DIAG-005 (SRS version 9). Verification repeated: SRS-CTL-020 to
SRS-CTL-023 and SRS-CTL-034 (the protocol and its handling of every field, which now include
`diagnostics` and its `events` field), SRS-CTL-033 (the API version), SRS-SEC-002 (roles), and
the system requirements SRS-SYS-001 and SRS-SYS-002, whose runs now record events.

### Software items and safety class

Changed: core (the flight recorder), rt (the crash report), service and readout (they record
events), protocol (the command and the version), access (the role of the command), server (the
option and the handler) and ctl (the subcommand). All class B; no class or segregation changes.
The recorder is written on control paths only, never per single or per packet.

### Risk

H-05 (acquisition interrupted): the signal handler is a new piece of code that runs when the
process is already failing; it must not turn a crash into a hang. It reads only static memory,
calls only async-signal-safe functions, and resets itself on entry (`SA_RESETHAND`), so a second
fault ends the process. H-01 (data lost without notice): no change to the data path or to the
integrity verdict; recording an event takes no lock the pipeline waits on. H-08 (unauthorized
control): `diagnostics` reads and changes nothing, needs an observer, and returns numbers only.
No estimate in the risk file changes.

### SOUP

None. The handler uses glibc's `dl_iterate_phdr` at start-up only, and POSIX functions.

### Interfaces and data formats

The control API becomes 2.1: one new command and its response; no existing request or response
changes, so 2.0 clients keep working (ADR 0003). The server's new option is optional. The
crash report is a text format for people, not an interface; its first line identifies it. The
list-mode format and the configuration schema do not change.

### Documents

ADR 0016 (new); the ADR index; the SRS, version 9; the trace matrix; the software items and their
paths (unchanged items, new files); the code review checklist (new, Chapter 21); the problem
reports (a root-cause field); the CHANGELOG.

### Regulatory

The intended use does not change, and no safety-relevant function changes. Diagnostic data that
leaves the device through the control API is a new data flow for the security risk assessment
(threat model, Chapter 17): it holds no personal data and no secrets, which the test of the
command checks by its fields (assumption: confirm with team whether the product's diagnostics
must also be listed in the instructions for use and the cybersecurity documentation).

## Verification

Unit tests of the recorder (FlightRecorder.KeepsAThreadsEventsInTheOrderItRecordedThem,
FlightRecorder.ASnapshotTakenWhileThreadsRecordNeverShowsHalfAnEvent under ThreadSanitizer,
FlightRecorder.CountsTheEventsOfThreadsThatFindNoFreeRing), of the report
(CrashReport.TheBuildIdIsTheOneTheLinkerWrote, CrashReport.AReportNamesTheSignalTheProgramAndTheLastEvents)
and death tests that crash a child process
(CrashReportDeathTest.AFaultWritesTheReportAndTheProcessStillDiesOfIt,
CrashReportDeathTest.AnAbortWritesTheReportAndTheProcessStillDiesOfIt); the protocol test
ControlProtocol.DiagnosticsReturnTheNewestEventsOfTheFlightRecorder and the extended
ControlProtocol.EveryFieldOfEveryTypeIsAnswered; the system test of a crashed server and its
postmortem; the measurement of the cost of an event (`measurements/ch21/`); all presets of
`ci/run_all.sh` and the static analysis.

## Decision

Approved on 2026-10-26 by the software lead and the risk manager: a diagnostic aid on control
paths, without SOUP, verified by tests that crash on purpose; the API change is additive.
