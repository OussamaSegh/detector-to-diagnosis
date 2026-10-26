# FPGA firmware and the interface contract {#ch24}

::: box-why
Every word MiniDAQ receives was made by firmware: logic in an FPGA on a front-end board that
timestamps a SiPM's pulse, packs it, holds it in a FIFO and sends it. You will not write that
firmware, but as the lead of the DAQ software you share a boundary with the people who do, and
most of the hard bugs of a data acquisition system live on that boundary: a status bit that one
side reads before the other has set it, a counter that tears when it is read in two halves, a
stop that leaves the last events on the board, a new firmware release that moves a field. This
chapter teaches you to read a small firmware module and its timing diagram, to recognize the
handshakes, clock domains and FIFOs that firmware is built from, and to model them in C++ to
check a design; then to write down the contract between firmware and software in an interface
control document, to check at run time that the boards run firmware the software was written
for, and to sequence a run's start and stop so that no event waits on a board when the run is
judged complete.
:::

**A day in the life.** The physicists report that the last frame of every dynamic acquisition
counts 1.5% fewer events than the frame before it, on every detector block, at every activity.
The run records say every run is complete. You plot the singles rate of the last second of a run
in 10 ms bins: flat, then nothing for the final 60 ms, as if the detector had gone blind before
the operator pressed stop. You ask the firmware lead how a board stops. "We clear the trigger
enable, and the FIFO drains over the link; there's a FIFO_EMPTY bit, we added it in 1.2." The
software stopped its receiver at the same moment it cleared the triggers, so whatever the
boards still held arrived at a closed socket. Nobody had read FIFO_EMPTY because nobody had
written down that it existed. By the end of the week there is a stop sequence that waits for
every board to report its FIFO empty, a check that refuses boards with firmware older than 1.2,
and a twelve-page interface control document that both leads have signed.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Explain what an FPGA is made of, how firmware is built and verified, and why that makes
   firmware changes slower and more expensive than software changes.
2. Read a small SystemVerilog module and its timing diagram, and model it cycle by cycle in C++ to
   check it against its specification.
3. Recognize a valid/ready handshake and back-pressure, and check a recorded trace against the
   handshake's rules.
4. Explain metastability and why a multi-bit value crosses a clock domain in Gray code or through
   a FIFO, and read a counter wider than a register without tearing it.
5. Size a FIFO from its rates and bursts, and sequence a run's start and stop so that every event a
   board took is inside the run.
6. Write an interface control document with a firmware team, check firmware compatibility at run
   time, and decide which functions belong in firmware and which in software.

## Prerequisites and estimated time {.unnumbered}

Chapter 9 (the readout link), Chapter 15 (the fault tree of H-01), Chapter 22 (registers and the
slow control) and Chapter 23 (the receive path). No prior knowledge of hardware description
languages is needed. Reading: about 3 hours. Exercises: 3 to 4 hours. Milestone: 4 hours. If time
is short, do Exercises 24.3 and 24.4.

## What an FPGA is, for a software engineer

### The intuition

A processor runs one instruction after another. A field-programmable gate array (FPGA) runs
nothing: it is a grid of small hardware blocks whose connections are set when the chip is
configured at power-up, and every block works at the same time, on every clock edge. Firmware
for an FPGA is not a program; it is a description of a circuit. Its building blocks are:

- **Lookup tables (LUTs)**: each computes any logic function of a few inputs (four to six,
  depending on the family), by storing its truth table.
- **Flip-flops**: each holds one bit and takes a new value only at a rising clock edge. Every
  piece of state in firmware is a flip-flop or a memory.
- **Block RAM**: small memories of tens of kilobits each, used for FIFOs and buffers. A FIFO of
  4,096 64-bit words, the one on MiniDAQ's board, is 256 kbit of them.
- **DSP blocks** for multiplications, **clock managers** that make the clocks, and **I/O**
  including serial transceivers for links of many gigabits per second.

Because everything runs at once, an FPGA does in one clock cycle what software would do in a
loop, and it does it with a fixed, known latency: a timestamp taken by a time-to-digital converter
in the FPGA is accurate to tens of picoseconds, which no operating system can promise for
anything.

### From source to bitstream

Firmware is written in a hardware description language (HDL), VHDL or SystemVerilog, and goes
through steps that have no exact equivalent in software:

1. **Simulation.** A testbench drives the design's inputs and checks its outputs, cycle by cycle,
   in a simulator. This is where firmware is tested, because inside the chip almost nothing can
   be observed.
2. **Synthesis** turns the description into LUTs, flip-flops and memories.
3. **Place and route** puts them on the chip and wires them together.
4. **Timing analysis** checks that every path from one flip-flop to the next settles within one
   clock period. A design that fails "timing closure" works in simulation and fails on the chip,
   sometimes, depending on temperature.
5. The **bitstream** is written to a flash memory on the board, from which the FPGA loads at
   power-up.

Steps 2 to 4 take minutes for a small design and hours for a large one, and a change of one line
can make a design that met timing fail it. For the software lead this has three consequences.
A firmware change is slow and has to be planned, so the interface between firmware and software
should be agreed before either side builds on it. The firmware team's evidence is its
simulations, so ask for the testbench, not only the bitstream. And a firmware version is a
build of a circuit, so it must be identified, recorded and checked like any other configuration
item (Chapter 20).

### Reading a small module

The listing below is the output stage of MiniDAQ's front-end board, in SystemVerilog: the FIFO
between the event logic and the data link that this chapter is about. It is in the repository to
be read (`hw/rtl/feb_out_fifo.sv`); MiniDAQ does not build it, its tests use the C++ model of the
board, and the test `hw.rtl` simulates the listing against its testbench with Icarus Verilog
where that simulator is installed (tool TL-26).

```{.verilog include="hw/rtl/feb_out_fifo.sv" snippet="module"}
```

Read it with four rules in mind.

- **`always_ff @(posedge clk)`** describes flip-flops: everything in the block happens at the
  rising edge of `clk`, at the same instant. The right-hand sides are the values *before* the
  edge; `<=` (a non-blocking assignment) schedules the new values for after it. So
  `count <= count + 1'b1` and `if (pop) rd_ptr <= ...` do not see each other's results; they all
  read the old state.
- **`assign`** and **`wire`** describe logic without memory: `full`, `push` and `pop` are
  recomputed continuously from the current state and inputs, and `out_valid` is high whenever the
  count is not zero.
- **Parameters** (`WIDTH`, `DEPTH_LOG2`) are fixed when the design is built: the depth of the FIFO
  is a property of the bitstream, not something software can change.
- **Every decision is visible in the code.** This FIFO refuses an event when it is full even if
  the link takes a word in the same cycle (`push` uses the old `full`); a lost event sets
  `overflow` even if software clears it in the same cycle (the set comes first); nothing enters
  while `trigger_enable` is 0; and `fifo_empty` is simply "the count is zero". Each of these is a
  fact the software depends on, and each belongs in the interface control document.

### A timing diagram

Firmware engineers explain a design with a timing diagram: the signals over a few clock cycles.
Here is the same FIFO with a depth of 2, triggers on, as a table of rising edges. Each row shows
the inputs before the edge and the state after it.

| Edge | `in_valid` (data) | `out_valid` before | `out_ready` | `overflow_clear` | Word taken | `level` after | `overflow` after |
|---:|---|---|---|---|---|---:|---|
| 1 | 1 (A) | 0 | 0 | 0 | none | 1 | 0 |
| 2 | 1 (B) | 1 | 0 | 0 | none | 2 | 0 |
| 3 | 1 (C) | 1 | 1 | 0 | A | 1 | 1 |
| 4 | 0 | 1 | 1 | 1 | B | 0 | 0 |
| 5 | 1 (D) | 0 | 1 | 0 | none | 1 | 0 |
| 6 | 0 | 1 | 1 | 0 | D | 0 | 0 |

At edge 3 the FIFO is full, so C is lost and the flag is set, although A leaves in the same cycle.
At edge 5, D is written while the link is ready, but it cannot leave until edge 6: a word needs
one cycle to get through. Reading a diagram like this is a skill worth practicing, because it is
how the firmware team will answer most of your questions.

### Checking firmware without the hardware

The testbench `hw/rtl/feb_out_fifo_tb.sv` drives the FIFO with 20,000 cycles of random events and
a random link, in four phases (a slow link, a fast link twice, then the triggers off), and checks
every output against a model written as plainly as possible: a circular buffer and a count. It
was itself checked by planting two defects in the listing, a clear that wins over a set and a
push into a full FIFO; it caught both. Exercise 24.3 asks you to write the same model in C++ and
run it on the same stimulus, which is exactly what a software lead contributes to a firmware
review: an independent reading of the specification, executable.

The same idea scales up. `FakeBoard` (Chapter 22) is an executable specification of the whole
board, which MiniDAQ's tests run against at simulated time. A firmware team that uses Verilator,
which compiles SystemVerilog into C++, can run MiniDAQ's own tests against the real RTL, and
cocotb lets them write testbenches in Python (assumption: confirm with team which simulators the
firmware team uses and whether a shared co-simulation is worth setting up).

## Handshakes and back-pressure

### Valid and ready

Inside an FPGA, and between FPGAs, data moves as streams with a two-signal handshake. The sender
drives `valid` and the data; the receiver drives `ready`; a word moves at a clock edge where both
are 1. The rules, as Arm's AXI4-Stream specification states them for its `TVALID` and `TREADY`
and as most FPGA streams follow them, are:

1. A word moves in a cycle where `valid` and `ready` are both 1.
2. Once `valid` is 1, it stays 1 until the word has moved.
3. While `valid` is 1 and the word has not moved, the data does not change.
4. The sender does not wait for `ready` before it raises `valid`. The receiver may wait for
   `valid` before it raises `ready`.

Rule 4 prevents a deadlock in which each side waits for the other; it cannot be seen in a single
trace, because a deadlocked stream looks like an idle one. Rules 2 and 3 can, and Exercise 24.1
checks them in a recorded trace.

### Back-pressure, and where it must stop

A receiver that lowers `ready` pushes back: the sender holds its word, and if the sender is itself
a receiver, it lowers its own `ready` in turn. Back-pressure travels upstream until it reaches
something that can wait. In a data acquisition system, the front of the chain cannot: a photon
that hits a crystal does not wait for a network switch. So the first buffer in the chain, the
board's output FIFO, is where back-pressure becomes loss, and that is why this FIFO drops events
and counts them, while everything after it, the network stack and MiniDAQ's pipeline, can push
back or must count what it drops (Chapter 23, Chapter 3).

## Clock domains

### Metastability

Every flip-flop needs its input to be stable for a short window around the clock edge (its setup
and hold times). A signal that comes from another clock, or from outside the chip, changes at
moments unrelated to this clock, and sooner or later it changes inside that window. The
flip-flop can then go *metastable*: its output hovers between 0 and 1 for an unbounded time
before it settles, to either value. Logic that reads it while it hovers can see a 0 in one place
and a 1 in another.

The standard remedy for a single bit is a synchronizer: two flip-flops in a row, clocked by the
receiving clock. The first may go metastable; the second samples it one full clock period later,
by which time it has almost certainly settled. "Almost certainly" is a number: the mean time
between failures grows exponentially with the time allowed for settling, and with the right
design it is many times the age of the universe. R. Ginosar's tutorial (Further reading) gives the
formula and the parameters that the FPGA vendor publishes for it.

### Multi-bit values

A synchronizer makes one bit safe to read, but it decides nothing about *which* value is caught:
the old or the new. For one bit, either is a correct reading of some moment. For a binary counter
going from 7 (`0111`) to 8 (`1000`), four bits change at once, each is caught old or new on its
own, and the receiving side can read any of 16 values, 14 of which the counter never held.

Firmware avoids this in three ways:

- **Gray code**, for counters such as a FIFO's pointers: consecutive values differ in exactly one
  bit, so a sample is always the old value or the new one. An asynchronous FIFO, whose write and
  read sides run on different clocks, passes its pointers across in Gray code (C. Cummings'
  paper is the classic description). Exercise 24.2 builds the encoding and shows that a pointer
  that arrives a cycle late is harmless: the read side sees fewer words than there are, never
  more.
- **A handshake** for an arbitrary value: the value is held stable, and a single request bit is
  synchronized; the receiver samples the value only after it has seen the request.
- **An asynchronous FIFO** for a stream.

### The same problem, seen from the bus

Software meets the same problem whenever it reads something that the board changes on its own
clock. A 64-bit timestamp counter exposed as two 32-bit registers can carry between the read of
the low half and the read of the high half, and the value read is then 2^32^ counts away from
the truth: 67 seconds at a 64 MHz clock. The remedy in software is to read high, low, high, and
to try again when the high half changed; the remedy in firmware is to copy the high half into a
shadow register when the low half is read, which makes the order of the two reads part of the
contract. Exercise 24.4 does the first.

A status register has the same property in time. A read is a snapshot of one moment: a status
read *before* software writes a control bit says nothing about the board *after* the write. The
run stop later in this chapter depends on exactly that.

## FIFOs: filling, draining and depth

A FIFO absorbs the difference between two rates for as long as it has room. With words arriving
at a rate *in* and leaving at a rate *out*, a FIFO of depth *D*:

- fills from empty in *D* / (*in* - *out*) when *in* is larger, and never fills otherwise;
- drains *n* words in *n* / *out* once nothing comes in;
- survives a burst of length *T* without loss when *D* is at least (*in* - *out*) *T*.

The board's FIFO holds 4,096 words and its link, in this book's simulation, sends 25,000 words
per second. Events at 50,000 words per second fill it in 164 ms; at 27,000 words per second they
take 2.05 s; a full FIFO drains in 164 ms once the triggers are off. The last number is the one
the software must know: it bounds how long a stop has to wait for the board, and it changes
whenever the firmware team makes the FIFO deeper or the link slower. That makes the FIFO's depth
part of the interface, not an internal detail of the firmware. Exercise 24.3 computes these
numbers and models the FIFO cycle by cycle.

A FIFO only absorbs bursts. If the average rate in is above the rate out, no depth is enough; the
fix is a faster link, less data per event, or fewer events.

## The interface control document

### What it contains

An interface control document (ICD) is the contract between two teams that build the two sides
of one interface. Each side can then be built and tested against the document without the other,
and a change to the document is a change on both sides. MiniDAQ's is `docs/hw/icd-feb.md`
(ICD-FEB), a controlled document of the design file (Chapter 16) that the software lead owns and
the firmware lead co-signs. Its sections are the questions every such interface has to answer:

| Section | Answers |
|---|---|
| Scope | Which interfaces (control path, data path, sequences, versions), and what is out of scope |
| Terms | What a word, the output FIFO, "drained" and a cycle mean |
| Versions and compatibility | Which firmware implements which register map and data format, and which the software accepts |
| Control path | Access width and alignment, access types, what an absent board looks like, timing |
| Sequences | Power-up, run start, run stop, fault and acknowledgment, step by step, with who does what |
| Data path | The datagram format, order and numbering, what happens when the FIFO is full |
| Responsibilities | For each failure, what the firmware does and what the software does |
| Open items | What is not yet decided, with an owner |
| Verification | Which test shows each statement |

Three properties make an ICD useful rather than decorative. It is **specific**: "sets `fifo_empty`
only when the last word has left the board" is testable; "handles the FIFO correctly" is not. It
**lists what is open**: ICD-FEB says that whether `fifo_empty` includes the link's own buffer is
not yet confirmed, instead of letting each side assume. And it is **traced**: section 9 names the
test of every statement, and the SRS requirements that implement it (SRS-HW-011 to SRS-HW-015)
point back to it.

### Three versions

The board carries three versions, and the ICD says how they relate:

- the **firmware version** in `fw_version`, MAJOR.MINOR.PATCH: MAJOR for a change of meaning or a
  removal, MINOR for an addition, PATCH for a fix;
- the **register map version** in `hw/feb.toml`, which this chapter moves to 1.1 by adding
  `status.fifo_empty`, `error_flags.fifo_overflow` and the register `fifo_level`;
- the **data format version** in every datagram's header (Chapter 9).

Firmware 1.0 and 1.1 implement register map 1.0, which has no FIFO status; firmware 1.2 and
every later 1.x implement map 1.1. MiniDAQ 0.5 accepts 1.2 and later 1.x, and refuses the rest.

### Checking the firmware at run time

The slow control reads `fw_version` from every board in every cycle and latches a fault on a board
whose firmware is not supported, before it believes any other register of that board
(SRS-HW-011, risk control RC-31):

```{.cpp include="minidaq/src/hw/slow_control.cpp" snippet="firmware-check"}
```

Three choices are deliberate. The check runs **every cycle**, not once at start-up, because a
board can be swapped or reflashed while the software runs, and the test
`SlowControl.RefusesFirmwareItWasNotWrittenFor` reflashes one under a running slow control.
A board of another **major** version is not believed at all, because the same address may hold
another quantity in another unit: a temperature read as a bias, or worse, a bias written as a
threshold. And the supported versions are **compiled into the software**, in
`SlowControlSettings`, not read from the hardware description: a configuration file that could
widen them would let an installation run firmware that nobody verified with this software. The
release notes of each MiniDAQ version name the firmware it supports, and the installation record
names the firmware installed, which the status now reports for each board.

::: box-regulated
- **The ICD is a design output.** IEC 62304 expects the software requirements to include the
  software's interfaces, hardware interfaces among them, and the architecture to identify them;
  ICD-FEB is where those interfaces are specified, and it is controlled like the SRS (version,
  history, review, change requests on both sides).
- **Firmware is part of the device.** Whether a manufacturer develops FPGA firmware under its
  software life cycle (IEC 62304) or under its hardware design process differs between companies,
  and the answer decides which records the firmware team keeps (assumption: confirm with team).
  Either way, the combination of firmware and software versions that was verified together is a
  configuration item, and the software's check enforces it.
- **A refused board is a safe state.** The check latches a fault with bias and triggers off; the
  operator sees the reason ("firmware 1.1.3 is not supported: this software needs 1.2 or a later
  1.x") and the service will not start a run.
:::

## A run's edges

### Start: the pipeline first, then the triggers

A board sends data while its `trigger_enable` bit is set, and it is the service's job to set it at
the right moment. Data that arrives before the pipeline reads it waits in the socket buffer, and
at a high rate overflows it (Chapter 23), so the order is: start the pipeline, then switch the
triggers on.

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="start-sequence"}
```

The slow control owns the boards' registers, so the service asks it rather than writing to the
boards itself:

```{.cpp include="minidaq/include/minidaq/hw/slow_control.hpp" snippet="trigger-api"}
```

`set_triggers` wakes the slow control's thread at once rather than waiting up to a period (100
ms), and the next cycle applies it. The service's monitor then waits until `triggers_are(true)`
says that a cycle has done it, and faults the run when the boards have not done it within the
trigger timeout, 2 s by default (SRS-HW-012). A run whose boards silently ignored the request
would otherwise be an empty run judged complete;
`HardwareService.ARunWhoseBoardsDoNotSwitchTheirTriggersOnEndsInAFault` shows that it is not.

### Stop: the triggers off, then wait for the boards

At a stop, the order reverses, with a wait in the middle: switch the triggers off, wait until
every board has sent what its FIFO holds, and only then stop the pipeline.

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="stop-sequence"}
```

The monitor, which runs every 20 ms, watches for the drain:

```{.cpp include="minidaq/src/control/acquisition_service.cpp" snippet="board-sequence"}
```

The subtle part is in the slow control, where "drained" is decided. A cycle reads every register
first and writes afterwards, so the cycle that switches a board's triggers off has read its
`fifo_empty` *before* the write. That reading says nothing about the moment after the write: an
event could have entered the FIFO in between. So the cycle that writes the triggers off marks the
FIFO's state as unknown, and only a later cycle's reading can say the board is drained:

```{.cpp include="minidaq/src/hw/slow_control.cpp" snippet="triggers"}
```

`SlowControl.SwitchesTheTriggersWhenAskedAndSaysWhenItHasDone` checks exactly this: after the
write, `drained()` is false although the FIFO was empty, and only the next cycle makes it true.

### What the stop costs

The measurement `measurements/ch24/run_sequence.py` runs the server with two simulated boards,
starts five runs of about 1 s per scenario, and times each stop from the audit trail, from the
`stop` command to the transition into `configured`. The first board always has a link 50 times
faster than its events; the second board's rates are the scenario's.

| Scenario | Stop to configured, ms (min / median / max) | Board 1's FIFO at stop, words | FIFO overflows | Drain timeouts | Complete runs |
|------------------------------|---------------------:|--------------:|------------:|-----------:|-----------|
| No hardware | 3 / 15 / 21 | n/a | n/a | n/a | 5 of 5 |
| Link 50 times faster than the events | 123 / 137 / 140 | 0 | 0 | 0 | 5 of 5 |
| Backlog of 2,000 words | 123 / 132 / 138 | 2,000 | 0 | 0 | 5 of 5 |
| FIFO overflows (50,000 in, 25,000 out) | 221 / 224 / 236 | 4,096 | 11 | 0 | 0 of 5 |
| Link stalled (drain timeout 500 ms) | 523 / 538 / 539 | 4,096 | 10 to 12 | 5 | 0 of 5 |

Read it as arithmetic. Without boards, a stop is the pipeline's own drain plus up to one monitor
period of 20 ms. With boards, the woken cycle switches the triggers off at once and the next cycle,
one period of 100 ms later, confirms the drain: about 120 ms. A backlog of 2,000 words drains in
80 ms, inside that period, so it costs nothing more. A full FIFO takes 164 ms, so the second cycle
after the switch confirms it: about 220 ms. A stalled link never drains, and the stop waits for
the drain timeout and then marks the run incomplete. Every one of the 20 runs with boards was
judged correctly: complete when everything arrived, incomplete when the board lost data or kept
it.

The cost is at least one slow-control period per stop, which ADR 0019 accepts: nothing in the
intended use needs a faster stop. If something did, the slow control could read the FIFO's status
every few milliseconds while it waits for a drain, instead of once per period.

### Losses the board reports

Two more losses now count in the integrity verdict (SRS-HW-015, risk control RC-30): the overflows
of each board's FIFO since its triggers went on, which the slow control counts and clears every
cycle, and a drain that ran out of time. They appear in the status and the run record as
`/hardware/boards/N/fifo_overflows` and `/hardware/drain_timeouts`, next to Chapter 23's
`socket_drops`. The overflow count is a lower bound: the flag is one bit, and one cycle that finds
it set may stand for one lost event or a thousand. That is enough to judge a run incomplete,
which is the verdict's purpose; a firmware that should say *how many* events it lost needs a
counter register, which is an addition to the ICD.

One loss remains outside the verdict: datagrams lost on the network after the last one that
reaches the host (Chapter 23). Closing it needs the board to report how many datagrams it sent,
which ICD-FEB lists as an open item for register map 1.2.

## What belongs on which side

Some functions could live in either the firmware or the software, and the choice is made once,
expensively, because moving a function across the boundary later changes the ICD, both code
bases and their verification. These are the criteria that decide it:

- **Time scale.** Anything that must happen within nanoseconds of an event (timestamping, pulse
  integration, discrimination) or within microseconds of a fault belongs in firmware. A loop with
  a period of 100 ms belongs in software.
- **Data rate.** Firmware reduces data before it leaves the board: a pulse becomes one word.
  Sending raw samples to the PC instead would multiply the link's rate.
- **Change frequency and cost.** Calibration, policies, formats and anything a physicist will want
  to adjust are cheaper to change, test and release in software.
- **Independence.** A protection that must work when the software has crashed belongs in firmware
  or in hardware, and the software adds its own, stricter limit on top: two independent layers.
- **Visibility.** Software can log, count, report and be debugged on a running system; firmware
  mostly cannot. A function whose behavior must be explained afterwards favors software, or
  firmware that reports what it did.

Applied to MiniDAQ's board:

| Function | Where | Why |
|---|---|---|
| Timestamp, energy, crystal of each single | firmware | nanoseconds, and the data reduction |
| Output FIFO, drop-and-count on overflow | firmware | the front cannot be back-pressured |
| Overtemperature (60 C) and overcurrent cut-off | firmware | works without software; independent layer |
| Temperature alarm (40 C), bias law, setpoint limits | software | slow, calibrated, configurable, a second layer |
| Run sequencing | software, with firmware status bits | orchestration across boards; firmware reports its state |
| Coincidence sorting across boards | software in MiniDAQ | needs every board's singles; many scanners do it in a central FPGA instead |
| Loss accounting | both | each side counts what only it can see; the software judges |

::: box-mistakes
- **Stopping the receiver when the triggers go off.** The boards still hold data. Wait for every
  board to report its FIFO empty, in a reading made after the write.
- **Trusting a status read made before a write.** It describes the moment before. Read again.
- **Reading a counter in two halves once.** It tears at every carry of the low half. Read high,
  low, high, or agree on a shadow register in the ICD.
- **Checking the firmware version once at start-up.** Boards are swapped and reflashed. Check in
  every cycle, and refuse what was not verified.
- **Making the supported firmware configurable.** A configuration that widens it bypasses the
  verification of the combination.
- **Keeping the interface in people's heads.** The bit that nobody wrote down is the one nobody
  reads. If it is not in the ICD, it does not exist for the other team.
- **Assuming a FIFO absorbs everything.** It absorbs bursts. Compute the time to fill from the
  rates, and the drain time that the stop must wait for.
:::

::: box-askteam
1. Is there an interface control document between the firmware and the software, who owns it,
   and when did both sides last review it against what is built?
2. How does the software know which firmware each board runs, and what does it do with a version
   it was not verified with?
3. How does a run stop: in which order are the triggers, the boards' buffers and the receiver
   stopped, and how does the software know a board has sent everything?
4. Which counters does the firmware keep for lost or dropped events, and are they in the run's
   integrity verdict?
5. Which simulator and testbenches does the firmware team use, and can the software's tests run
   against the firmware's RTL?
6. Which values cross clock domains or are wider than a register, and how is each one read
   safely?
:::

## Exercises {.unnumbered}

**Exercise 24.1 (M): Check a valid/ready handshake.** *Goal:* from a recorded stream, count the
transfers, stalls and idle cycles and the longest back-pressure, and report every violation of
the handshake's rules 2 and 3 with its cycle. *Starter:*
`exercises/ch24/e1_handshake/starter/handshake.cpp`. *Acceptance:* `tests/test_handshake.cpp`
passes: back-to-back words, ready without valid, a valid dropped before its transfer, data that
changed while waiting, and the longest stall. Then answer in `NOTES.md` why one trace cannot show a
breach of rule 4. *Time:* 45 minutes.

**Exercise 24.2 (E): Gray code across clock domains.** *Goal:* encode and decode Gray code, count
the bits that change, and compute how many words the read side of an asynchronous FIFO may read
from a synchronized write pointer. *Starter:* `exercises/ch24/e2_gray_code/starter/gray_code.cpp`.
*Acceptance:* `tests/test_gray_code.cpp` passes: one bit per step also at the wrap, a torn sample
that is the old or the new value, and wrapped pointers. Then answer in `NOTES.md` why a pointer
that arrives late is harmless. *Time:* 30 minutes.

**Exercise 24.3 (M): The board's output FIFO, cycle by cycle.** *Goal:* model
`hw/rtl/feb_out_fifo.sv` in C++, edge by edge, and compute the time to fill, the drain time and
the depth for a burst. *Starter:* `exercises/ch24/e3_out_fifo/starter/out_fifo.cpp`.
*Acceptance:* `tests/test_out_fifo.cpp` passes: refusal when full also while the link takes a
word, nothing while the triggers are off, set wins over clear, 20,000 cycles of random traffic
against a plain model, and this chapter's numbers. Then answer in `NOTES.md` why the board drops
the new event rather than the oldest word. *Time:* 60 minutes.

**Exercise 24.4 (M): A counter wider than a register.** *Goal:* read a 64-bit counter exposed as
two 32-bit registers while it keeps counting, without ever returning a torn value. *Starter:*
`exercises/ch24/e4_split_counter/starter/split_counter.cpp`. *Acceptance:*
`tests/test_split_counter.cpp` passes: a carry during the read at six moments, a high half that
never holds still, and failed reads. Then answer in `NOTES.md` how firmware can remove the problem
and what the ICD must then say. *Time:* 45 minutes.

## MiniDAQ milestone: the boards' firmware under contract {.unnumbered}

::: box-milestone
**Goal.** The interface with the boards' firmware is written down and checked: an interface
control document, register map 1.1, a firmware check in every slow-control cycle, a run whose
triggers go on after the pipeline starts and whose stop waits until every board has drained, and
an integrity verdict that counts the boards' own losses. **Start:** tag `ch23`. **End:** tag
`ch24`.
:::

1. Write change request CR-0010 and ADR 0019; add SRS-HW-011 to SRS-HW-015 and extend SRS-HW-004,
   SRS-HW-007 and SRS-HW-010 (SRS version 13); add risk controls RC-30 (H-01) and RC-31 (H-10);
   update the architecture description (version 10).
2. Write `docs/hw/icd-feb.md` and add it to the controlled documents of the design file.
3. Move `hw/feb.toml` to version 1.1 and regenerate the header and the table; give `FakeBoard` a
   firmware version, an output FIFO with its rates and the fault `stalled_link`.
4. In the slow control: the firmware check, `set_triggers` with a wake-up, `triggers_are`,
   `drained` with the reading after the write, the overflow count, and bias and triggers off in
   one write on a fault.
5. In the service: the start and stop sequences with their timeouts, triggers off at a fault, at
   the end of a finite run and at a reset, the new status fields (control API 2.3) and the losses
   in the integrity verdict; the hardware description 1.1 with the run's timeouts.
6. Add the measurement `measurements/ch24/run_sequence.py`, the listing `hw/rtl/` with its
   testbench and the test `hw.rtl`, and Exercises 24.1 to 24.4.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-HW-011 to SRS-HW-015 tested; the measurement judges every run
correctly; every starter of the chapter fails. Tag `ch24`.

## Check yourself {.unnumbered}

1. Name four kinds of blocks an FPGA is made of, and say which of them holds state.
2. Why can a firmware design pass every simulation and still fail on the chip? Which step is
   supposed to catch that?
3. In `always_ff`, what does a right-hand side read: the value before the edge or after it? What
   would change in the FIFO if `push` used the count after the pop?
4. State the four rules of a valid/ready handshake. Which one prevents deadlock, and why can no
   single trace prove it was followed?
5. Why must the board's output FIFO drop events instead of pushing back, while MiniDAQ's pipeline
   may push back?
6. A two-flip-flop synchronizer makes a bit safe to read. Why does it not make a 13-bit binary
   pointer safe, and what does Gray code change?
7. A 64-bit counter at 100 MHz is read as two 32-bit registers, low then high, once. How far off
   can the result be, how often, and how do you fix it in software and in firmware?
8. Events arrive at 40,000 words per second and the link sends 30,000. How long until a 4,096-word
   FIFO overflows, and how long does it take to drain once full?
9. Why does the slow control refuse to call a board drained in the cycle that switched its
   triggers off, even when that cycle read `fifo_empty` as 1?
10. A stop with boards took about 120 ms in this chapter's measurement and one without took about
    15 ms. Where do the extra 100 ms come from, and how would you cut them if you had to?
11. Why are the supported firmware versions compiled into MiniDAQ instead of being read from the
    hardware description?
12. The physicists want the energy window applied on the boards to cut the link's rate. Which
    criteria decide whether it belongs in firmware, and what changes in the ICD if it moves there?

## Summary {.unnumbered}

- An FPGA is a circuit, not a program: LUTs, flip-flops, block RAM and clocks, all working at
  every edge. Firmware is verified in simulation and built through synthesis, place and route and
  timing analysis, which makes changes slow; agree on the interface before building on it.
- Read HDL with its rules: `always_ff` blocks happen at the edge from the old state, `assign` is
  logic without memory, parameters are fixed at build. Every decision of a module, such as
  refusing when full or set winning over clear, is a fact that software depends on.
- Streams move with valid/ready handshakes; back-pressure travels upstream until it reaches
  something that cannot wait, and in a DAQ that is the first FIFO, where it becomes counted loss.
- A value that crosses clock domains is caught old or new, bit by bit. Single bits cross through
  synchronizers, counters in Gray code, streams through asynchronous FIFOs. Software sees the same
  tearing in a counter wider than a register: read high, low, high.
- A FIFO absorbs bursts: it fills in D / (in - out) and drains in n / out. The board's 4,096 words
  drain in 164 ms at 25,000 words per second, which bounds a stop.
- ICD-FEB records versions, the control and data paths, the sequences, the responsibilities and
  the open items, with a test for each statement. The slow control refuses unsupported firmware in
  every cycle (RC-31).
- A run starts its pipeline before the triggers and stops it only after every board has drained,
  judged from a reading made after the triggers went off; overflows and drain timeouts are losses
  (RC-30). It costs one slow-control period per stop, measured at about 120 ms.
- Put in firmware what needs nanoseconds, reduces data or must protect without software; put in
  software what changes, needs calibration or must be explained afterwards; count losses on both
  sides.

## Further reading {.unnumbered}

- Arm, *AMBA 4 AXI4-Stream Protocol Specification*, ARM IHI 0051A, 2010: the valid/ready
  handshake rules in their most widely used form.
- C. E. Cummings, "Simulation and Synthesis Techniques for Asynchronous FIFO Design", SNUG San
  Jose 2002: Gray-coded pointers and the full and empty conditions, with code.
- C. E. Cummings, "Clock Domain Crossing (CDC) Design & Verification Techniques Using
  SystemVerilog", SNUG Boston 2008: synchronizers, multi-bit crossings and how to verify them.
- R. Ginosar, "Metastability and Synchronizers: A Tutorial", *IEEE Design & Test of Computers*
  28(5), 2011: the failure rate of a synchronizer, with the formula.
- S. L. Harris and D. M. Harris, *Digital Design and Computer Architecture*, RISC-V edition,
  Morgan Kaufmann, 2021: an introduction to digital logic and SystemVerilog for programmers.
- IEEE Std 1800, *SystemVerilog: Unified Hardware Design, Specification, and Verification
  Language*: the language reference.
- AMD, *UltraFast Design Methodology Guide for FPGAs and SoCs* (UG949): how a vendor recommends
  structuring, constraining and closing timing on a design; useful to understand what the firmware
  team spends its time on.
- NASA, *Systems Engineering Handbook*, NASA/SP-2016-6105 Rev2, 2016: section 6.3 on interface
  management and interface control documents.
- The Icarus Verilog and Verilator projects (steveicarus.github.io/iverilog, verilator.org): open
  source simulators for reading and running small designs such as `hw/rtl/feb_out_fifo.sv`.
