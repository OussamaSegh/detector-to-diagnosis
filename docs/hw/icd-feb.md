# Interface control document: MiniDAQ software and the front-end board firmware

Version 6 (MiniDAQ 2.0.0-dev). Status: approved for release 2.0.0, 2026-11-16, given by the coordinator under the software lead's standing delegation of 2026-11-15; the firmware lead's co-signature is not recorded (assumption: confirm with team).
Document ID: ICD-FEB. Owner: the software lead; the firmware lead co-signs every version.

This document is the contract between the two sides of the front-end board (FEB): the firmware
that runs in the board's FPGA and the MiniDAQ software that controls the board and receives its
data. Each side can be built and tested against this document without the other. A change to
anything in it is a change request on both sides (`docs/regulatory/changes/`), and the document's
version changes with it. The board in this project is simulated (`minidaq/src/hw/fake_board.cpp`);
the statements marked "assumption: confirm with team" are the ones a real firmware team has to
confirm or correct.

## 1. Scope

| Interface | Direction | Defined in |
|---|---|---|
| Control path: 32-bit registers over a memory-mapped bus | software reads and writes, firmware answers | section 4; `hw/feb.toml`, generated into `docs/hw/feb-register-map.md` |
| Data path: MDQ-R datagrams over UDP | firmware sends, software receives | section 6; ADR 0009, `minidaq/include/minidaq/format/readout_packet.hpp` |
| Sequences: power-up, run start, run stop, fault, acknowledgment | both | section 5 |
| Versions and compatibility | both | section 3 |

Out of scope: the board's power supplies, its clock distribution (only the lock of its sampling
clock's phase-locked loop is part of this contract, register map 1.3), the SiPM front-end analog
chain and the firmware's internal design, which are the firmware team's own documents.

## 2. Terms

- **Word**: one MDQ-P1 single, 8 bytes (`packed_single.hpp`).
- **Output FIFO**: the buffer on the board between the event logic and the data link; it holds
  4,096 words (32 KiB).
- **Drained**: the triggers are off and the output FIFO is empty: every word the board took has
  left the board.
- **Time marker**: an MDQ-P1 word with crystal 32767 and energy code 2047 (MDQ-P1 revision 1.1,
  `packed::marker`). Its time field is a promise: no later word of the same board has an earlier
  time. No crystal of the scanner has the ID 32767, so a decoder that does not know markers drops
  them as invalid singles.
- **Cycle**: one pass of the software's slow-control loop over every board, every 100 ms by
  default (`SlowControlSettings::period`).

## 3. Versions and compatibility

Three versions are independent of each other and each is carried where the other side can read
it:

| Version | Where it is | Who changes it |
|---|---|---|
| Firmware version, MAJOR.MINOR.PATCH | register `fw_version` (0x004) | firmware team, at every firmware release |
| Register map version | `hw/feb.toml` `[map] version`, and the header of `feb-register-map.md` | both, by change request |
| Data format version | the `version` byte of every MDQ-R datagram | both, by change request |

The rules for the firmware version:

- **MAJOR** changes when a register keeps its address but changes its meaning, a register or
  field is removed, or the data format's version changes. Software written for one major version
  does not trust a board of another.
- **MINOR** changes when registers or fields are added and the old ones keep their meanings.
  Software that needs an addition requires at least the minor version that brought it.
- **PATCH** changes for fixes that change no register's meaning.

Which firmware implements which map, and what this software accepts:

| Firmware | Register map | Data format | MiniDAQ 0.5 |
|---|---|---|---|
| 1.0.x, 1.1.x | 1.0 (no FIFO status) | 1 | refused: the run stop cannot know when the board has drained |
| 1.2.x | 1.1 | 1 | supported |
| 1.3.x | 1.2 (time markers, datagrams sent) | 1, with MDQ-P1 revision 1.1 words | supported; markers and the datagram count used |
| 1.4.x and later 1.x | 1.3 (clock status) | 1, with MDQ-P1 revision 1.1 words | supported; the clock status used as well |
| 2.x | not defined | not defined | refused |

The software checks the firmware version of every board in every cycle, not once at start-up,
because a board can be swapped or reflashed while the software runs: a board whose version is
not supported latches a fault (cause `firmware`) before any other of its registers is believed
(SRS-HW-011, risk control RC-31). The supported versions are compiled into the software
(`SlowControlSettings::firmware_major`, `firmware_min_minor`); no configuration file can widen
them.

## 4. Control path

- Every register is 32 bits wide at an address that is a multiple of 4; the software accesses it
  with exactly one aligned 32-bit load or store (SRS-HW-009). The firmware must not depend on
  byte or 16-bit accesses.
- An access to an address that the map does not define reads as 0 and its write has no effect.
  The software never makes one.
- Access types are those of the map: `ro`, `rw`, `wo` (reads as 0), `rw1c` (writing 1 to a bit
  clears it, writing 0 leaves it). The firmware sets a sticky flag in `error_flags` and keeps it
  set until the software clears it, whatever else happens.
- A board that is absent or has lost its link answers every read with `0xFFFFFFFF` (a PCIe device
  that has gone) or makes the access time out; the software treats either as "no answer" and
  latches a fault after 3 cycles in a row (SRS-HW-004).
- `status` describes the present and changes on its own; `error_flags` records events since the
  software last cleared them. A condition that matters both now and afterwards is in both
  (`overtemp` and `overtemp_trip`).
- Timing: a register access completes within 10 us (assumption: confirm with team for the real
  bus). A write takes effect in the board before the next read of any register returns.

## 5. Sequences

### 5.1 Power-up of a board

1. Read `board_id`: `magic` must be `0x4D51`, or the software latches a fault (`identity`).
2. Read `fw_version`: section 3.
3. Write `bias_ramp_rate`, then `bias_setpoint`, then set `control.bias_enable` (SRS-HW-002), so
   that the supply never drives a setpoint left from before.
4. The board is ready when `status.bias_ready` is set and the measured bias is within 100 mV of
   the setpoint (SRS-HW-001 to SRS-HW-005).

### 5.2 Run start

| Step | Software | Firmware |
|---|---|---|
| 1 | Refuses `start` while a board is not ready (SRS-HW-006). | |
| 2 | Starts its receiving pipeline. | |
| 3 | Clears `error_flags.fifo_overflow`, then sets `control.trigger_enable` on every board, at once rather than at the next cycle. | Starts taking events into the output FIFO and sending them. |
| 4 | Confirms in a cycle that every board's triggers are on; ends the run in a hardware fault when they are not within the trigger timeout, 2 s by default (SRS-HW-012). | |

The pipeline starts before the triggers, so that no datagram arrives before something reads it.

With firmware 1.3 or later, step 3 also writes `marker_interval` (in microseconds, 100 by
default, `SlowControlSettings::marker_interval_us`) and sets `control.marker_enable` in the same
write as `trigger_enable` (SRS-HW-016). The firmware resets `datagrams_sent` to 0 on the rising
edge of `trigger_enable`. An interval of 0 in the software leaves the markers off.

### 5.3 Run stop

| Step | Software | Firmware |
|---|---|---|
| 1 | Clears `control.trigger_enable` on every board. | Stops taking events; keeps sending what the FIFO holds. |
| 2 | Reads `status.fifo_empty` in a cycle after the write of step 1 (a status read before the write says nothing about after it). | Sets `fifo_empty` only when the last word has left the board, including any buffer of the link behind the FIFO (assumption: confirm with team that the MAC's buffer is included). |
| 3 | When every board is drained, or the drain timeout (2 s by default) has passed, stops the pipeline (SRS-HW-013). A drain that ran out of time makes the run incomplete (SRS-HW-015). | |

Stopping the pipeline first would leave the run's last events in the socket or on the board and
could still judge the run complete; this order is risk control RC-30. The cost is at least one
cycle: on the book's virtual machine a stop took 123 to 140 ms with the boards against 3 to 21 ms
without them (`measurements/ch24/run_sequence.txt`).

### 5.4 Fault and acknowledgment

- A latched fault on a board makes the software write 0 to `control`: bias and triggers off in
  one write (SRS-HW-004). The service also switches every board's triggers off when a run faults,
  ends on its own or is reset (SRS-HW-014).
- An operator's reset acknowledges the faults: the software clears the sticky flags it acted on
  and powers the board up again; a cause that remains latches again in the next cycle (SRS-HW-005).

## 6. Data path

- Datagrams follow MDQ-R version 1 (ADR 0009): a 16-byte header with a per-source sequence
  number, then 1 to 1,024 words; at most 182 words in a standard 1,500-byte MTU.
- The firmware sends a board's words in time order and numbers its datagrams consecutively from 0
  at every run start (assumption: confirm with team whether the sequence restarts at the trigger
  enable or at a soft reset).
- With `control.marker_enable` set (firmware 1.3 and later), the board puts a time marker into
  its stream at every multiple of `marker_interval` of its clock, after every word with an earlier
  time and before every word with a later one, also while it takes no event. The software's
  sorter closes the coincidence windows before a marker without waiting for a later single
  (SRS-FMT-014, SRS-PIPE-013, SRS-SRT-014), which bounds the latency of a run's last
  coincidences when a detector falls silent (problem report MDQ-PR-007). A marker is a word of
  the stream like any other: it takes a place in the FIFO and in a datagram and is counted in
  `datagrams_sent`. The marker's time must not be earlier than a word sent before it (assumption:
  confirm with team that the marker is inserted after the event logic's own reordering).
- `datagrams_sent` (firmware 1.3 and later) counts the datagrams the board has handed to the link
  since `trigger_enable` was last set; a datagram is counted when it leaves the board. The
  software reads it every cycle; when every board reports it, the run's integrity verdict counts
  the datagrams sent beyond those the link delivered or counted as lost as a loss (SRS-HW-017,
  `/hardware/datagrams_unaccounted`). This finds the datagrams lost on the network after the last
  one that reached the software, which no sequence gap can show (the residual of ADR 0018).
- `clock_status` (firmware 1.4 and later) gives the lock of the phase-locked loop that makes the
  board's sampling clock from the reference, and counts the times the loop lost lock since
  `trigger_enable` was last set (at most 65,535). A board's time stamps count that clock: a loop
  that loses lock and locks again can come back a few hundred picoseconds away, which keeps the
  order of the board's words and moves every coincidence of its block (hazard H-02). The software
  reads it every cycle after it switches the triggers; it starts no run while a board's loop is
  not locked, records an audit event `clock_lock_lost` when a count grows during a run, and the
  run's integrity verdict counts the losses (SRS-TIM-006, risk control RC-54). A lost lock is not
  a fault: the bias stays on. The firmware must count a loss even when the loop locks again
  before the next read (assumption: confirm with team that the count is kept in the loop's own
  clock domain, not sampled).
- When the output FIFO is full, the board drops the new event, not words already in the FIFO, and
  sets `error_flags.fifo_overflow`. It never sends a partial event.
- The software counts each cycle that finds `fifo_overflow` set, clears the flag, and the run's
  integrity verdict counts a nonzero count as a loss (SRS-HW-015). The count is a lower bound of
  the events lost: one cycle's flag can stand for many.
- The FIFO's depth is part of this contract because the software's run stop and the integrity
  verdict depend on it: at the depth of 4,096 words and a link of 25,000 words per second, a full
  FIFO drains in 164 ms. A firmware that deepens the FIFO increases the drain time the software
  must wait, and the drain timeout must cover it.

## 7. Responsibilities when something goes wrong

| Condition | Firmware does | Software does |
|---|---|---|
| Temperature above 60 C | Switches the bias off, sets `overtemp` and `overtemp_trip` | Latches a fault (its own alarm is at 40 C) |
| Bias current above the board's limit | Sets `overcurrent` | Latches a fault |
| Output FIFO full | Drops the event, sets `fifo_overflow` | Counts it as a loss, clears it |
| Unsupported firmware | | Latches a fault, bias and triggers off |
| Triggers not on after start | | Faults the run after the trigger timeout |
| FIFO not empty after stop | Keeps sending | Stops the pipeline after the drain timeout; the run is incomplete |
| Datagrams sent that never arrived (firmware 1.3) | Counts every datagram it sends | Counts the difference as a loss; the run is incomplete |
| Sampling clock not locked (firmware 1.4) | Clears `pll_locked`, counts the loss | Starts no run; during a run, an audit event and a loss; the run is incomplete |

## 8. Open items

| Item | Owner | Status |
|---|---|---|
| A counter of datagrams sent per run in the board, so that the software can find loss on the network after the last datagram that reached it (the residual of ADR 0018) | both | closed in version 3: register map 1.2, `datagrams_sent` (CR-0026) |
| Whether `datagrams_sent` is the count of datagrams handed to the MAC or of datagrams on the wire | firmware | open (section 6) |
| The simulated board counts its datagrams from its FIFO model, not from the link: a simulated board with firmware 1.3 together with the UDP detector can report datagrams the link never carried. The hardware description's simulated boards therefore report firmware 1.2.0 | software | open; a real board or a simulated link with the board's own count closes it |
| The real bus's access time and whether a posted write can be overtaken by a read | firmware | open (section 4) |
| Whether `fifo_empty` includes the link's own buffer | firmware | open (section 5.3) |
| When the datagram sequence restarts | firmware | open (section 6) |

## 9. Verification

| Statement | Verified by |
|---|---|
| Unsupported firmware is refused, every cycle | `SlowControl.RefusesFirmwareItWasNotWrittenFor` |
| Triggers on after the pipeline, confirmed, faulted on timeout | `SlowControl.SwitchesTheTriggersWhenAskedAndSaysWhenItHasDone`, `HardwareService.TheTriggersAreOnOnlyWhileARunTakesData`, `HardwareService.ARunWhoseBoardsDoNotSwitchTheirTriggersOnEndsInAFault` |
| Drained only on a status read after the write, and only with an empty FIFO | `SlowControl.SwitchesTheTriggersWhenAskedAndSaysWhenItHasDone`, `SlowControl.SaysDrainedOnlyOnceTheFifoIsEmpty` |
| Overflows and drain timeouts are losses | `SlowControl.CountsFifoOverflowsAsLostDataNotAsAFault`, `HardwareService.AStopWaitsForTheBoardsAndADrainThatRunsOutOfTimeIsALoss`, `RunIntegrity.TheBoardsLossesCount` |
| A fault switches bias and triggers off | `SlowControl.ALatchedFaultSwitchesTheBiasAndTheTriggersOff` |
| Markers enabled with the triggers on firmware 1.3, never on 1.2; `datagrams_sent` read every cycle | `SlowControl.SwitchesTheTimeMarkersOnWithTheTriggersAndReadsTheDatagramsSent`, `FakeBoard.HasTheRegistersOfMap12OnlyWithFirmware13` |
| A marker is no single and closes the windows before it, with no change to any coincidence | `TimeMarker.IsAWordThatNoSingleOfTheScannerCanBe`, `StreamDecoder.ReadsAMarkerAsAPromiseNotASingle`, `CoincidenceSorter.MarkersChangeNoCoincidence`, `Pipeline.MarkersChangeNoCoincidence`, `Pipeline.AMarkerDeliversTheLastCoincidencesWhileTheSourceIsSilent` |
| Datagrams sent and never seen are a loss | `RunIntegrity.DatagramsTheBoardsSentButTheLinkNeverSawAreALoss` |
| The clock status read every cycle on firmware 1.4, never on 1.3; no run without a lock; a loss during a run is an audit event and a loss | `FakeBoard.HasTheClockStatusOfMap13OnlyWithFirmware14`, `SlowControl.ReadsEachBoardsClockAndStartsNoRunWithoutALock`, `HardwareService.AClockThatLosesLockDuringARunIsAnAuditEventAndALoss`, `RunIntegrity.ABoardClockThatLostLockMakesTheRunIncomplete` |
| The register map is generated and checked | `docs.regmap`, `Registers.TheGeneratedMapMatchesItsSpecification` |

## 10. Changes

| Version | Change |
|---|---|
| 1 | First version: register map 1.1, firmware 1.2 and later 1.x, data format 1 (Chapter 24, CR-0010, ADR 0019). |
| 2 | Approved by the software lead for release 1.1.0; the content is that of version 1 (MDQ-PR-066). |
| 3 | Register map 1.2 of firmware 1.3: time markers (`control.marker_enable`, `marker_interval`, MDQ-P1 revision 1.1) and `datagrams_sent`; the open item on datagrams sent closed (Chapter 24, CR-0026, ADR 0033). |
| 4 | Approved for release 1.3.0, given by the coordinator under the software lead's standing delegation of 2026-11-15; the content is that of version 3. |
| 5 | Register map 1.3 of firmware 1.4: `clock_status`, the sampling clock's lock and its lock losses per run (Chapter 38, CR-0031, ADR 0037). |
| 6 | Approved for release 2.0.0, given by the coordinator under the software lead's standing delegation of 2026-11-15; the content is that of version 5. |
