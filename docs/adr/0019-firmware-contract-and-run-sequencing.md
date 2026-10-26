# 0019. An interface control document with the firmware, a firmware check every cycle, and a run stop that waits for the boards to drain

Date: 2026-10-26
Status: Accepted

## Context

Chapter 22 gave MiniDAQ a register map and a slow-control loop for the front-end boards, and
Chapter 23 counted every datagram lost between the network card and MiniDAQ. Two gaps remained
at the boundary with the boards' firmware.

The first is versions. The register map has a version and the board reports a firmware version
in `fw_version`, but nothing tied the two together, and the software read every board as if it
ran the firmware it was written for. A register map from another major version can put another
meaning at the same address: the software would then read a temperature or write a bias in the
wrong units without any error.

The second is the run's edges. The service started its pipeline and the boards sent data whenever
their `trigger_enable` bit was set, which nothing in the software set; and a stop stopped the
pipeline at once. A board holds events in its output FIFO until its link has sent them, so
stopping the pipeline first drops the run's last events on the board or in the socket, and no
counter on the host can see them: the run is judged complete (fault tree of H-01, events E5 and
E6). A FIFO that overflows during a run loses events on the board, which only the board's own
flag shows.

## Options

1. **Leave the firmware boundary informal.** Each side follows the register map; the order of a
   run's start and stop is whatever each side does. Nothing to write, and the gaps stay.
2. **Check the firmware version once, at start-up, and sleep for a fixed time at stop.** Simple;
   misses a board that is swapped or reflashed later, and a fixed sleep is either too short for a
   full FIFO, which loses data silently, or too long for every other run.
3. **A written contract and a sequence that confirms each step.** An interface control document
   that both teams sign, with the versions the software supports, the order of a run's start and
   stop, and the meaning of the FIFO's status bits; a firmware check in every cycle; triggers on
   after the pipeline starts, confirmed by a read; at stop, triggers off and the pipeline stopped
   only when a read made after the switch shows every FIFO empty, with a timeout that makes the run
   incomplete rather than hang it.

## Decision

Option 3. `docs/hw/icd-feb.md` (ICD-FEB, version 1) is the contract: firmware 1.2 and later 1.x implement
register map 1.1, which adds `status.fifo_empty`, `error_flags.fifo_overflow` and `fifo_level`.
The slow control latches a fault on a board whose firmware is not supported, in every cycle
(SRS-HW-011, RC-31). The service switches the triggers on after its pipeline has started and
faults the run when the boards have not done it within the trigger timeout (SRS-HW-012); at stop,
it switches them off and stops the pipeline once every board is drained or the drain timeout has
passed (SRS-HW-013); overflows and a drain that timed out are losses (SRS-HW-015, RC-30). The
supported firmware versions are compiled into the software, not read from a configuration.

## Consequences

### Positive

- A board with firmware the software was not written for is never believed, whenever it appears.
- The run's first and last events are inside the run: every event a board took has left it before
  the run is judged, or the run is incomplete with the reason in its integrity verdict.
- The firmware team has one document to build and test against, and its open questions are
  listed in it instead of being discovered on a scanner.

### Negative

- A stop takes at least one slow-control cycle longer: 123 to 140 ms against 3 to 21 ms without
  boards on the book's virtual machine (`measurements/ch24/run_sequence.txt`). A shorter period
  while draining would cut it; nothing in the intended use needs that yet.
- Every cycle reads two more registers per board, `fw_version` and `fifo_level`: 8 reads instead
  of 6.
- Loss on the network after the last datagram that reaches the host remains invisible until the
  board counts the datagrams it sent (ICD section 8, planned for register map 1.2).
- The decision is revisited when a real firmware team answers the open items of the ICD,
  especially whether `fifo_empty` includes the link's own buffer.
