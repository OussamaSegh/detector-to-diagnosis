# CR-0009: Drop counters of the receive path, including the datagrams dropped at the end of a run

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-26, by the software lead |
| Source | measurement: Chapter 9's burst runs left 164 packets unaccounted for, and Chapter 23's runs showed the sequence gaps undercounting the socket's drops by up to 2,071 packets (fault tree of H-01, event E6) |
| Decision | approved, 2026-10-26, software lead and risk manager |
| Commits | 2389c6c |

## Description

The UDP detector adapter asks the kernel for the datagrams it dropped at MiniDAQ's socket:
`SO_RXQ_OVFL` attaches the count to every datagram, and the drops column of `/proc/net/udp` has it
at any time. The adapter reports the larger of the two as the counter `socket_drops`, and the run
integrity verdict counts a nonzero value as a loss. The adapter also reports the host's UDP
counters (`/proc/net/snmp`), the receive backlog's counters (`/proc/net/softnet_stat`) and, when the
receiving interface is known, the network card's counters (`/sys/class/net/IF/statistics`), as
their changes since the adapter was opened. A new module, `minidaq/net/host_counters`, parses those
files. A benchmark measures the cost of receiving by call and batch size.

## Reason

A datagram dropped after the last one that arrives leaves no gap in the sequence numbers, so the
loss at the end of a burst or a run was not counted, and a run that lost its last packets could be
judged complete (H-01). The host's own counters also let an operator tell a loss on the network
from a loss in the PC, which needs a different remedy.

## Impact analysis

### Requirements

New: SRS-RDO-013 (the socket's drops, including the tail), SRS-RDO-014 (the host's counters as
changes, only those it can read) and SRS-RDO-015 (the verdict counts the socket's drops), SRS
version 12. Verification repeated: SRS-RDO-010 to SRS-RDO-012 (the adapter), SRS-CTL-030 and
SRS-CTL-031 (the integrity verdict and its audit record).

### Software items and safety class

Changed: readout (class B), which gains the module `net/host_counters` (core layer: it parses text
and reads files, and includes no socket header); service (class B), whose integrity verdict counts
one more counter. No class or segregation changes. The host's counters are read on the control
thread when the status is asked for, never on the data path; the drop count of each datagram is
read from its ancillary data in the receive loop, which costs no system call.

### Risk

H-01 gains RC-29 (the socket's drops, including the tail, are counted and make the run incomplete).
The host's counters are explanations, not risk controls: they include other sockets and other
interfaces, so they do not decide the verdict. Loss on the network after the last datagram that
reaches the host remains invisible to the receiver (residual, to be closed with the sender's count
in the interface with the firmware, Chapter 24).

### SOUP

None new. The Linux kernel (platform SOUP) is now also the source of the drop counters; their
formats are tested with captured text, and a missing or changed file leaves the counter out rather
than reporting zero.

### Interfaces and data formats

No change to the control API's version: `detector_counters` is an open set of named counters
(ADR 0013), which gains `socket_drops`, `socket_queue_bytes`, `host_udp_*`, `host_softnet_*` and
`nic_*`. A client that judged a run by `packets_lost` alone should use the integrity verdict, as the
intended use already says. The configuration and the list-mode format do not change.

### Documents

ADR 0018 (new); the ADR index; the architecture description, version 9 (which also records Chapter
22); the SRS, version 12; the trace matrix; the risk file (RC-29); the software items and the layers
(`net/`); the CHANGELOG.

### Regulatory

The intended use does not change. The installation and verification records of a system should
include `net.core.rmem_max` and the receive buffer the status reports (Chapter 9's regulated box).

## Verification

Unit tests of the parsers and the reader (HostCounters.ReadsTheUdpCountersByColumnName,
HostCounters.SumsTheBacklogCountersOfEveryCpu, HostCounters.FindsOneSocketByItsInode,
HostCounters.ReportsOnlyWhatBothReadingsHave, HostCounters.ReadsTheFilesBelowARoot), of the adapter
over the loopback interface (UdpDetector.CountsTheDatagramsItsSocketDroppedEvenAtTheEnd,
UdpDetector.TheKernelsDropCountArrivesWithTheNextDatagram,
UdpDetector.ReportsTheHostsCountersAsChangesSinceItOpened) and of the verdict
(RunIntegrity.EveryLossCounterMakesTheRunIncomplete); the measurements
`measurements/ch23/drop_accounting.txt`, where every datagram sent was delivered or counted as a
socket drop in 18 runs of 18; all presets of `ci/run_all.sh` and the static analysis.

## Decision

Approved on 2026-10-26 by the software lead and the risk manager: a new risk control for an
existing hazard, in existing class B items, with no change to an interface's version.
