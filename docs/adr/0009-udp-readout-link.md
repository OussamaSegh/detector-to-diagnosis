# 0009. UDP readout link with sequence numbers and a bounded reorder buffer

Date: 2026-10-24
Status: Accepted

## Context

Chapter 9 connects MiniDAQ to a readout link instead of an in-process simulator. The link
carries MDQ-P1 words from a detector (or `minidaq_send`) to the acquisition PC at up to tens
of thousands of packets per second. The detector cannot wait for the PC, so whatever
transport we choose, data can be lost when the PC falls behind. The pipeline's sort stage
cannot repair singles that arrive out of time order, and the service faults the run if it
sees any (Chapter 6), so the receiver must deliver each link's words in order. Every lost or
discarded packet must be counted and reported (data integrity, Chapter 1). The receiver must
be testable without a network, and must survive arbitrary datagrams on its port.

## Options

1. **UDP datagrams with a sequence number per source, and a bounded reorder buffer in the
   receiver.** One packet per datagram (format MDQ-R1). Loss is not prevented but made
   visible; the receiver holds early packets for a bounded window and time, then declares the
   gap lost. Simple for an FPGA to send; standard tools work; no back-pressure on the
   detector.
2. **TCP.** No loss on the network and in-order delivery by the protocol. Retransmissions
   add at least a round-trip of delay and stall all later data (head-of-line blocking); the
   sender must buffer everything unacknowledged; when the receiver is slow, the loss moves
   into the detector's buffers, where nothing counts it. Not practical in an FPGA without a
   hardware TCP stack.
3. **UDP without sequence numbers.** The simplest receiver, but loss, reordering and
   duplication become invisible; a lost packet looks like a lower count rate.
4. **A dedicated link (PCIe, a custom optical protocol).** Higher bandwidth and lower latency
   in exchange for special hardware on the PC and a driver; not needed at MiniDAQ's rates and
   not available on a developer's laptop.

## Decision

Option 1. MDQ-R1 packets (`minidaq/format/readout_packet.hpp`) carry a magic, a version,
flags, a source id, a 32-bit sequence number and a word count, and are validated field by
field. `readout::SequenceTracker` (core layer) restores sequence order within a window of 64
packets (a power of two) and a hold time of 1 ms by default, counts every packet as
delivered, lost, stale or rejected, and treats a run of stale packets or a jump of more than
2^24 packets as a restart of the source. `control::UdpDetector` (adapters layer) owns the
socket, receives with `recvmmsg`, reports the receive buffer the kernel actually granted, and
exposes the counters through `DetectorPort::counters()`. One adapter serves one source;
merging several links is the sorter's job (Chapter 10). The policy for runs with loss (fault
the run above a threshold, or flag the data) is left to the application.

## Consequences

### Positive

- Every datagram is accounted for, and the counters are in the status report; the loopback
  measurements of Chapter 9 match injected faults exactly when the hold time exceeds the
  reordering delay.
- The tracker is pure logic with an injectable clock: tested without sockets, fuzzed
  (`fuzz/fuzz_packet.cpp`), and reusable for other transports.
- The service and the pipeline did not change; the source type in the configuration
  (schema 1.1) selects the adapter.

### Negative

- Loss is possible by design. The receive buffer, the CPU and the network must be sized and
  verified on the target system, and `net.core.rmem_max` becomes part of the installation.
- Loss at the very end of a stream is invisible to sequence numbers; an end-of-run handshake
  or a running count from the sender is needed to close that gap (not yet implemented).
- Reordering larger than the hold time turns late packets into counted losses. The default
  of 1 ms suits a direct link; a switched network may need more.
- MDQ-R1 has no authentication: the readout network must be dedicated and separated, and the
  threat model must say so (Chapter 17).
