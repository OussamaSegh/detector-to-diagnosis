# Readout electronics and the event stream {#ch09}

::: box-why
Owning the sensor readout and the hardware controls means that you sit at the
boundary between the electronics team and the software. Everything the DAQ knows about a
photon arrives in a few bits of a hardware word, through a chain of ASICs, FPGAs and
network links that each have their own clocks, buffers and ways of failing. When a
coincidence rate drops by 2%, the cause can be a physics effect, a firmware threshold,
a time stamp that wrapped, a board whose clock drifted, or a socket buffer that the kernel
quietly made smaller than requested. Each looks the same in the image. This chapter teaches
you to read a hardware event-word specification, to reason about time stamps, clocks and
rollover, and to build a readout link that accounts for every packet. MiniDAQ gains a UDP
transport with sequence numbers, loss counters and rollover-safe time stamps.
:::

**A day in the life.** A long acquisition with the brain phantom shows a strange count-rate
curve. Trues follow the decay of the source smoothly, except for short dips of a few
percent, every few seconds, at the highest activities only. The sorter's logs show nothing
wrong. The physicists suspect dead time in the detector. You look at the link counters in
the status report instead. The UDP receiver counted a few hundred lost packets in the run,
and the operating system counted the same number of "receive buffer errors". The
configuration asked for an 8 MiB socket buffer, but the kernel's limit was 4 MiB, and at
peak rate the acquisition thread was descheduled just long enough to overflow it. The fix
is one line in the PC's system configuration and one line in the installation checklist.
The lesson is the one this chapter is built around: a readout path that counts every packet
turns a physics mystery into a ten-minute diagnosis.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Describe how a photodetector pulse becomes a digital time stamp and energy: leading-edge
   and constant-fraction timing, time walk, charge integration and time over threshold.
2. Read a hardware event-word or packet specification and write a decoder for it that is
   independent of the host's byte order and rejects every malformed input.
3. Explain coarse and fine time stamps, timestamp rollover, clock distribution and
   synchronization across boards, and correct a drifting clock from sync markers.
4. Identify the failure modes of a readout link (loss, reordering, duplication, corruption,
   clock drift, a board reset) and detect and count each one from the data.
5. Size a readout link: bandwidth, packet rate and socket buffers.

## Prerequisites and estimated time {.unnumbered}

Chapters 1 and 2 (strong types, the MDQ-P1 word), Chapter 3 (threads and queues), Chapter 6 (ports
and adapters, the configuration format) and Chapter 8 (the detector chain and the simulator). Basic
familiarity with sockets helps; the chapter explains what it uses. Reading: about 3 hours.
Exercises: 6 to 8 hours. Milestone: 5 hours.

## From a pulse to a time stamp and an energy

### The intuition

Chapter 8 ended at the photodetector: a crystal converts a 511 keV photon into a flash of a
few thousand optical photons, and a SiPM or PMT turns that flash into an electrical pulse.
The pulse carries the two things the DAQ wants. Its *start* is the time of the interaction,
and its *size* is the energy deposited. A front-end circuit must reduce the pulse to two
numbers, fast, for every channel, at rates of tens of thousands of pulses per second per
channel. How it does that decides the time resolution, the energy resolution and the dead
time of the whole scanner, and it decides which errors your software has to correct.

### Timing: leading edge, walk and constant fraction

The simplest timing circuit is a comparator with a fixed threshold: the time stamp is the
moment the pulse crosses it, the *leading edge*. It is fast and cheap, and it has a
systematic error called *time walk*. A small pulse rises more slowly in volts per
nanosecond than a large one, so it crosses the same threshold later. The figure shows it
on the pulse model of Exercise 9.4, a difference of exponentials with a 0.5 ns rise and a
40 ns decay.

![Leading-edge timing walks with amplitude; constant-fraction timing does not (pulse model of Exercise 9.4, threshold exaggerated).](src/img/ch09-time-walk.png){width=100%}

With a threshold at 2% of a 511 keV pulse, a 100 keV pulse crosses 44 ps later than a
511 keV pulse in this model. That is a large fraction of a 300 ps coincidence time
resolution, and it depends on energy, so it biases the time difference of every pair whose
photons deposited different energies. There are three remedies. A *walk correction* in
software subtracts a measured, energy-dependent delay from each time stamp. A *constant
fraction discriminator* (CFD) triggers at a fixed fraction of each pulse's own peak, which
for a fixed pulse shape removes the walk entirely; an analog CFD does it by comparing the
pulse with a delayed, attenuated copy of itself. And a *very low threshold*, at the level
of the first few detected optical photons, keeps the walk small because the earliest part
of the pulse rises steeply. Fast SiPM front ends commonly use the last approach and correct
the rest in software (verify: the timing method of your scanner's front end).

### Energy: charge integration and time over threshold

The pulse's size is best measured by its *charge*: integrate the current over a gate of a
few times the scintillator's decay time and digitize the result with an ADC. That is a
*QDC* (charge-to-digital converter) measurement. It is close to linear in the deposited
energy until the photodetector saturates. A SiPM has a finite number of cells, and when a
large fraction fire, more light no longer produces proportionally more charge.

A cheaper alternative is *time over threshold* (ToT): the time between the leading edge
and the moment the pulse falls back below the threshold. It needs no ADC, only a second
time stamp. Its price is nonlinearity. On the exponential tail of the pulse, the time to
fall to a threshold grows with the logarithm of the amplitude, so doubling the energy adds
the same τ_decay · ln 2 (27.7 ns for a 40 ns decay) whether you start at 30 or at 300 keV.
A ToT energy is compressed at high energies and needs a calibration curve per channel before
an energy window means anything. Exercise 9.4 measures both effects.

### Front-end ASICs

A scanner with tens of thousands of channels cannot afford discrete electronics per channel.
It uses application-specific integrated circuits that each serve tens of channels. Two
families appear often in PET research. The TOFPET2 ASIC from PETsys Electronics has 64
channels and provides a time stamp and either a charge or a ToT value per event (Bugalho et
al. 2019; verify: the details in the datasheet). Weeroc's PETIROC family is another
(verify: the current product names). Whatever the ASIC, it outputs per event a channel
number, a coarse and a fine time, an energy value, and sometimes flags. The ASIC's data goes
to an FPGA that collects many ASICs, applies thresholds and corrections, may form
coincidences itself, and packs the events into the words and packets that the acquisition
PC receives.

::: box-mistakes
- **Treating a time stamp as the photon's arrival time.** It is the time a circuit crossed a
  threshold, with a walk that depends on energy and a delay that depends on the channel.
  Both must be calibrated before time differences between channels mean anything.
- **Treating the energy value as keV.** A raw QDC or ToT value is in ADC counts or
  nanoseconds. It becomes keV only through a per-channel calibration, and a ToT value
  becomes keV only through a nonlinear one.
- **Calibrating once.** Gains of photodetectors change with temperature and bias voltage.
  A calibration is a function of the operating conditions, and the DAQ must record which
  calibration was applied to which data.
:::

## Time stamps: coarse, fine and clocks

### The intuition

A time stamp is a count of something. The coarse part counts cycles of a clock, a few
hundred megahertz in a front end, so its tick is a few nanoseconds. That is far too coarse
for a 300 ps coincidence time resolution, so a *fine* part interpolates within a tick. A
counter has a finite number of bits, so it wraps. And every board has its own oscillator,
so two boards' counters agree only if something makes them agree. Each of these three
facts is a source of bugs that look like physics.

### Coarse counters and fine interpolation

A *time-to-digital converter* (TDC) measures where within a clock tick an edge arrived.
Common designs are a chain of delay elements that the edge propagates through (in an FPGA,
a tapped delay line built from carry logic), a ring oscillator, or a time-to-amplitude
converter that charges a capacitor for the time between the edge and the next clock edge
and digitizes the voltage. They all produce a fine code that is not perfectly uniform:
some fine bins are wider than others (*differential nonlinearity*), and the widths drift
with temperature. A fine-time calibration measures each bin's width, typically by feeding
the TDC random, uniformly distributed edges and counting how often each code occurs, and
turns the fine code into a time through a table. The decoder in software then computes

> time = coarse × tick + calibrated_fine(code)

MDQ-P1, MiniDAQ's word from Chapter 2, uses an idealized version: a 28-bit coarse counter
with a 5.12 ns tick and a 10-bit fine part with 1,024 equal bins of 5 ps. Exercise 9.1
decodes a different, made-up word with a 40-bit coarse and a 10-bit fine part, close to
what a real TDC word looks like.

### Rollover

A counter of n bits wraps after 2^n^ ticks. MDQ-P1's 38-bit time code in 5 ps units wraps
every 2^38^ × 5 ps = 1.374 s. The 50-bit code of Exercise 9.1 wraps every 2^40^ coarse ticks
of 5.12 ns, 5,629.5 s or about 94 minutes. Both are ordinary situations: the first wraps
dozens of times per minute, the second once or twice in a long scan, and the rare one is
the more dangerous. A bug that shows up only after 94 minutes survives every test that runs
for an hour.

To reconstruct absolute time, the decoder counts wraps. The obvious rule, "the counter went
backwards, so it wrapped", is wrong as soon as words arrive slightly out of order, which
they do: different channels of an ASIC have different buffers, and an FPGA merges them. One
word that arrives 5 µs late would add a full wrap period to every later time stamp. The
correct rule compares the distance with half the range: a step back of more than half the
range is a wrap, a smaller step back is a late word, and a step forward of more than half
the range is a late word from before the latest wrap. This is MiniDAQ's `TimeUnwrapper`
from Chapter 2:

```{.cpp include="minidaq/include/minidaq/format/packed_single.hpp" snippet="unwrap"}
```

The rule holds as long as the stream is ordered to within half a wrap period, 0.69 s for
MDQ-P1, a margin no real readout comes near. It also survives the loss of packets, as long
as less than half a wrap period of data is missing at once.

### Clocks across boards

A scanner has many readout boards, and a coincidence compares time stamps from two of
them. Their counters must therefore count the same time. Two things can go wrong: an
*offset* (the counters were started at different moments) and a *drift* (the oscillators
run at slightly different rates). A crystal oscillator's frequency is accurate to some
tens of parts per million and changes with temperature. Two boards 20 ppm apart disagree by
20 µs after one second. That is 5,000 coincidence windows of 4 ns, so without correction no
coincidence between them would survive the first second.

Scanners solve this in one of two ways. Most distribute a common reference clock from one
source to every board (over dedicated cables or a backplane), lock each board's local clock
to it with a phase-locked loop, and send a synchronization pulse that resets all counters at
the same moment. Then there is no drift by construction, only a fixed offset per board that
a timing calibration measures and removes. The alternative, used in larger distributed
systems, is to let boards keep their own oscillators and synchronize them over the network
with a protocol such as IEEE 1588 PTP or its sub-nanosecond extension White Rabbit (Serrano
et al. 2009). Either way, the software must not *assume* synchronization; it must be able to
*detect* its loss. Exercise 9.3 simulates two boards with free-running clocks 20 ppm apart,
corrects them from periodic sync pulses with a piecewise linear map, and estimates the drift
from the coincidences alone:

```{.cpp include="exercises/ch09/e3_clock_drift/solution/clock_drift.cpp" snippet="correct"}
```

The second half of the exercise is the more useful one in practice. True coincidences have
a real time difference that averages to zero, so the peak of the distribution of
t~B~ − t~A~ for pairs between two boards sits at their relative offset. If one board drifts,
the peak moves. A histogram of t~B~ − t~A~ per one-second slice shows a drift of 1 ns per
second (1 part per billion) at once: the peak, a few hundred picoseconds wide, moves by
its own width within a second. That is a monitoring check the DAQ can run on every
acquisition, from data it already has.

::: box-mistakes
- **"The counter went backwards, so it wrapped."** True only for perfectly ordered data.
  Use the half-range rule, and test it with late words on both sides of a wrap.
- **Testing rollover by waiting for it.** A 94-minute wrap needs a test that starts the
  counter just before the wrap, not a 94-minute test. Every decoder needs a constructor or a
  test hook that sets the starting epoch.
- **Assuming the boards are synchronized because the hardware design says so.** A cable
  that is unplugged, a PLL that lost lock or a sync pulse that was missed all break it.
  Monitor the coincidence time peak per board pair, and treat a moving peak as a fault.
- **Unit drift.** A time in 5 ps codes, a time in coarse ticks and a time in picoseconds are
  all integers. Keep them in different types (Chapter 1's strong types) and convert at one
  place.
:::

## Reading a hardware event-word specification

### What a specification must say

The electronics team will hand you a document, often a table in a wiki, that describes what
their firmware sends. Before you write a line of the decoder, check that it answers every
question below. The ones it does not answer are the ones that become bugs.

- **Bit numbering and field boundaries.** Which bit is bit 0? Fields given as "bits 49 to
  10" are unambiguous; "the next 40 bits" is not.
- **Byte order.** In which order the bytes of a word travel and are stored. Network
  protocols traditionally use big-endian ("network byte order"); many FPGA designs and
  every x86 host use little-endian. A decoder written for one silently produces garbage on
  the other.
- **Units and scale.** What one count of each field means, including the fine time's bin
  width, whether it is calibrated, and whether energy is in ADC counts or keV.
- **Word types.** How a data word is distinguished from a status, sync or error word, and
  what the decoder must do with each kind.
- **Reserved bits and values.** Which bits must be zero today, and what a reader does if
  they are not. Accepting non-zero reserved bits today means a future format change cannot
  be detected.
- **Ranges and invalid values.** Which channel numbers exist, what a saturated energy looks
  like, whether a time code of zero is special.
- **Versioning.** How a reader learns which version of the format it is reading, and what
  changes are allowed without a new version.
- **Ordering guarantees.** Whether words are time-ordered per channel, per ASIC, per board,
  or not at all, and by how much they can be out of order.

### MDQ-R1: MiniDAQ's readout packet

MiniDAQ's simulated readout boards send their MDQ-P1 words in UDP datagrams, one *packet*
per datagram, in a format called MDQ-R1. Its specification is the header comment of
`readout_packet.hpp`, and every question above has an answer there:

```{.cpp include="minidaq/include/minidaq/format/readout_packet.hpp" snippet="header"}
```

Each field has a reason. The *magic* "MDQR" makes a stray datagram on the port (another
program, a port scan, a misconfigured board) fail on its first four bytes instead of being
decoded as data. The *version* lets the format change while old readers refuse new packets.
The *flags* carry the end of stream; undefined bits must be zero, so that a new flag cannot
be ignored by an old reader. The *source* identifies the link. The *sequence number*
increases by one per packet per source, which makes loss, reordering and duplication
visible. The *word count* and the datagram length must agree exactly, and the reserved field
must be zero. The parser checks every one of those, in that order, and never reads past the
end of the datagram:

```{.cpp include="minidaq/src/format/readout_packet.cpp" snippet="parse"}
```

### Worked example: a packet by hand

Here is the start of a datagram as a hex dump, the way you will see it in a packet capture:

```text
4d 44 51 52  01  00  02 00  f0 ff ff ff  02 00  00 00
e8 03 00 00 00 fe 01 07  01 a0 0f 00 c0 ff a8 48
```

Read it field by field. Bytes 0 to 3 are "MDQR". Byte 4 is version 1. Byte 5, the flags, is
0: not the end of the stream. Bytes 6 and 7, little-endian, are source 2. Bytes 8 to 11 are
the sequence number 0xFFFFFFF0, sixteen packets before the 32-bit wrap. Bytes 12 and 13 say
two words follow, so the datagram must be exactly 16 + 2 × 8 = 32 bytes long; a 33-byte
datagram is rejected as `bad_length`. Bytes 14 and 15 are the reserved zeros. The first word
starts at byte 16. As a little-endian 64-bit number, read from byte 23 down to byte 16, it is
0x0701FE00000003E8. Its top 15 bits are crystal 896, the next 11 are energy code 2,040, which
is 1,020 keV and almost saturated, and the low 38 bits are time code 0x3E8 = 1,000, which is
5,000 ps after the counter's last wrap. (These bytes were produced by `encode_packet`, not
typed by hand; the first attempt at typing them was wrong, which is the point of the
exercise.) Doing this once by hand, against the specification, is the fastest way
to find out whether you and the firmware engineer read the table the same way.

::: box-mistakes
- **C++ bit-fields for a wire format.** Their layout, order and padding are
  implementation-defined. Use shifts and masks on fixed-width unsigned integers (Chapter 2).
- **`reinterpret_cast` of the datagram buffer to a struct.** It assumes the host's byte
  order, the compiler's padding and the buffer's alignment, and it is undefined behavior
  under the aliasing rules. Read bytes and assemble integers explicitly, as `load_le` does.
- **Trusting the length field.** A packet that claims 1,000 words in a 100-byte datagram
  must be rejected, not read past the end of the buffer. This is the class of bug that
  fuzzing finds (Chapter 7). `parse_packet` checks the length before anything reads the
  payload, and the fuzz target `fuzz_packet` holds it to that.
- **Accepting unknown versions or flags "to be robust".** Robustness here means refusing
  what you do not understand, and counting it.
:::

## Data links

### The intuition

The words leave the FPGA on a physical link to the acquisition PC. The choice of link is
the electronics team's, but its properties shape your software: how many bytes per second
it carries, whether it can lose data, whether it can reorder it, and what happens when the
receiver is slow. Gigabit and 10-Gigabit Ethernet carrying UDP are a common choice in
research and medical DAQ systems, because an FPGA can send UDP without a full network stack,
the PC needs no special hardware, and standard tools (packet captures, switches, counters in
the operating system) work. PCIe and dedicated optical links are the alternatives when
bandwidth or latency demand them.

### Why UDP

UDP (RFC 768) sends independent datagrams. It does not retransmit lost ones, does not
reorder, does not slow the sender down when the receiver falls behind, and does not
guarantee delivery at all. TCP does all of those things, so why not use it? Because its
guarantees cost what a DAQ cannot pay. A retransmission adds at least a round-trip of delay
and stalls all data behind the lost segment (head-of-line blocking), and an FPGA would have
to buffer every unacknowledged byte to be able to resend it. A detector cannot wait for the
network: photons keep arriving. So readout links use UDP and make loss *visible* instead of
impossible: every packet has a sequence number, and the receiver counts what is missing. On a
dedicated network, with a correctly sized receiver, the count is zero, and when it is not,
the counters say so.

### The link budget

A datagram costs more than its payload. On Ethernet, each frame carries 14 bytes of header
and 4 of checksum, and occupies 8 more bytes of preamble and 12 bytes of inter-frame gap on
the wire. IPv4 adds 20 bytes and UDP 8. A full MDQ-R1 packet of 182 words, 1,472 bytes of UDP
payload, occupies 1,538 bytes of wire time. Exercise 9.5 turns that into the numbers that
matter:

```{.python include="exercises/ch09/e5_link_budget/solution/link_budget.py" snippet="wire"}
```

| Words per packet | Wire bytes per single | Singles/s, 1 Gbit/s | Singles/s, 10 Gbit/s | Packets/s at 10 M singles/s |
|---------:|----------:|----------:|----------:|-------------:|
| 182 | 8.45 | 14.8 M | 148 M | 54,945 |
| 32 | 10.56 | 11.8 M | 118 M | 312,500 |

: Ethernet link budget for MDQ-R1 (8-byte words, 16-byte header, IPv4, no VLAN tag).

At MiniDAQ's working rate of 10 M singles/s (Chapter 3), one Gigabit link is 68% full, too
little margin for the high-activity end of a count-rate test. A scanner of that class uses
10 GbE, several links, or coincidence filtering in the FPGA so that fewer singles leave the
detector (verify: your scanner's link type and count). The packet rate matters as much as the
byte rate: a receiving CPU pays a cost per packet, so small packets cost more than their
bytes suggest. With jumbo frames (a 9,000-byte MTU) a packet can hold over a thousand words,
which is why MDQ-R1 allows up to 1,024.

### Sequence numbers and serial arithmetic

A 32-bit sequence number at 55,000 packets per second wraps after 21 hours; a 16-bit one,
common in firmware, wraps after 1.2 seconds. Either way, comparisons must work across the
wrap. The technique is *serial number arithmetic* (RFC 1982): subtract the two numbers
modulo 2^32^ and interpret the result as a signed number. Small positive means "ahead",
small negative means "behind", whatever the absolute values:

```{.cpp include="minidaq/include/minidaq/format/readout_packet.hpp" snippet="serial"}
```

In C++20 the conversion of an out-of-range unsigned value to a signed type is defined to be
modular, so this one-liner has no undefined behavior. The same idea, with 16 bits, is the core
of Exercise 9.2, where a monitor counts loss, reordering and duplicates from a board's 16-bit
counter:

```{.cpp include="exercises/ch09/e2_link_monitor/solution/link_monitor.cpp" snippet="monitor"}
```

::: box-mistakes
- **Unsigned gap arithmetic.** `uint16_t(seq - expected)` for a packet one behind is 65,535,
  and a naive monitor counts 65,534 lost packets. Convert to signed, then compare.
- **Choosing TCP "to be safe".** On a readout link, TCP turns loss into latency and memory
  pressure on the sender. When the receiver falls behind, the detector's buffers overflow
  instead, where nobody counts them.
- **Ignoring the packet rate.** A link budget in bytes per second can look fine while the
  receiving core is saturated by packets per second. Budget both.
- **Ignoring IP fragmentation.** A datagram larger than the path's MTU is split into IP
  fragments, and losing any one fragment loses the whole datagram. Keep packets within the
  MTU, which is why MDQ-R1's default is 182 words.
:::

## Failure modes of a readout link

### What can go wrong

Each failure has a signature in the data. Learn to recognize them, because the first report
of each will come from someone who sees only its effect on an image.

- **Loss.** A packet never arrives: a full socket buffer on the PC (the most common cause),
  a full buffer in a switch, a bit error that fails the Ethernet checksum. Signature: a gap
  in the sequence numbers that never fills.
- **Reordering.** A packet arrives after a later one. Rare on a single cable, possible
  through switches with several paths or when the sender uses several transmit queues.
  Signature: a gap that fills shortly after.
- **Duplication.** The same packet twice, from a retransmission in a lower layer or a
  misconfigured network. Signature: a sequence number seen again.
- **Corruption.** Wrong bytes that passed every checksum, or a firmware bug. Signature:
  packets that fail the format checks, or values out of range.
- **Clock drift and lost synchronization.** Signature: a coincidence time peak that moves
  or broadens.
- **A board reset.** The board's sequence number and time stamps start again from zero.
  Signature: a long run of "stale" sequence numbers, and time going backwards.
- **Loss at the end.** The last packets of a stream are lost and nothing follows them.
  Signature: none in the sequence numbers. Only an end-of-stream marker, or the sender's own
  count, reveals it.

### What the DAQ must do about them

The receiver's job is narrow and strict: *detect, count, never hide*. It must not invent data
for lost packets, must not pass on data that would violate the ordering the rest of the
pipeline depends on, and must make every decision visible in its counters. Whether a run
with 0.01% loss is good enough for a clinical image is not the receiver's decision. It is a
policy that belongs to the application (a threshold that faults the run, or a flag in the
list-mode file for the analysis), and it can only be made if the numbers exist.

## MiniDAQ's UDP readout

### The design

The readout path has three parts, each in the layer where it belongs (Chapter 6):

- `readout::SequenceTracker` (core layer, no I/O) restores sequence order for one source and
  counts everything. It is pure logic with an injectable clock, so it is tested exhaustively
  without sockets.
- `control::UdpDetector` (adapters layer) owns the socket, receives datagrams in batches,
  parses them, passes valid ones through the tracker and delivers the words through the
  `DetectorPort` interface. The acquisition service and the pipeline do not change: the UDP
  detector replaces the simulated detector of Chapter 6 by configuration alone.
- `sim::Packetizer` and `sim::LinkFaults` (core layer) play the sending side for tests and
  for the tool `minidaq_send`.

```{.dot include="docs/architecture/components.dot" caption="MiniDAQ's components after this chapter: UdpDetector joins the adapters, and minidaq_send plays a readout board over UDP." width="100%"}
```

The tracker's statistics say what can happen to a packet:

```{.cpp include="minidaq/include/minidaq/format/readout_packet.hpp" snippet="stats"}
```

### Restoring order

The pipeline's sort stage (Chapter 3) counts singles that arrive out of time order, and the
service faults the run when there are any (Chapter 6), because nothing downstream can repair
them. A readout link is time-ordered only packet by packet.
So the tracker must deliver packets in sequence order, which means holding early packets
until the gap before them fills. It cannot hold them forever: a gap that never fills is a
loss, and every held packet adds latency. The tracker gives up on a gap when one of two
limits is reached: the *window* (64 packets by default) is full, or the gap has waited for
`max_hold_ns` (1 ms by default). Then it counts the missing sequence number as lost and
delivers what follows. A packet that arrives after its gap was given up is *stale*: it is
counted and dropped, because delivering it would put its words out of time order. The same
counter catches duplicates.

```{.cpp include="minidaq/include/minidaq/format/readout_packet.hpp" snippet="offer"}
```

Three details took more thought than the code suggests. First, the window must be a power of
two: slots are indexed by `sequence % window`, and only a divisor of 2^32^ keeps that mapping
one-to-one across the wrap from 2^32^ − 1 to 0. The constructor refuses any other size.
Second, a jump of a million sequence numbers (a long outage) is counted in one step rather
than one number at a time, so a corrupted sequence number cannot make the receiver loop for
seconds, and a jump of more than `max_gap_packets` (2^24^, minutes of data) is not counted
as loss at all but treated as a restart. Without that limit, a jump of about 2^31^ lands where
serial arithmetic is undefined, and the fuzz target `fuzz_packet` found within seconds that
the tracker then counted two billion lost packets. Third, a board that resets starts its numbering again, and from the tracker's point
of view every packet is then stale. More than one window's worth of stale packets in a row
is therefore taken as a restart: the tracker flushes what it holds, counts a *resync* and
follows the new numbering. The restarted board's time stamps also start again, so the run
then faults on time order. That is the right outcome, because a board reset in the middle of
a scan is a fault, and the counters say what happened.

### The adapter

The adapter receives with `recvmmsg`, which fetches up to 32 datagrams in one system call.
That matters at tens of thousands of packets per second, where a system call per packet is a
measurable share of a core. Every buffer is allocated when the adapter is opened. `read()`
does not allocate, and it receives only when everything delivered before has been read, so
that its buffer of pending words always has room for the worst case:

```{.cpp include="minidaq/src/control/udp_detector.cpp" snippet="read"}
```

The socket's receive buffer is where packets wait while the acquisition thread is busy or
descheduled. It is the most common cause of loss on a DAQ PC, and Linux makes it easy to get
wrong. `SO_RCVBUF` is capped at `net.core.rmem_max` without an error, and the value read back
is twice the useful size, because the kernel doubles it for its own bookkeeping (socket(7)).
The adapter reads the granted size back, halves it, and reports it in the status, with a
warning when it is smaller than requested:

```{.cpp include="minidaq/src/control/udp_detector.cpp" snippet="rcvbuf"}
```

The detector's counters reach the operator through a new, optional method of the
`DetectorPort` interface, `counters()`, which the service copies into the status report under
`detector_counters`. The configuration gains a source type and a section for the link. That
is a new minor version of the schema, 1.1, and Chapter 6's rule applies: a 1.1 reader accepts
1.0 files, and a 1.0 reader refuses 1.1 files.

```json
{
  "schema_version": "1.1",
  "source": {
    "type": "udp",
    "udp": { "address": "127.0.0.1", "port": 7701, "receive_buffer_bytes": 8388608,
             "reorder_window_packets": 64, "max_hold_us": 1000 }
  }
}
```

### The sending side and the fault injector

`minidaq_send` plays a readout board. It runs Chapter 8's detector simulator, encodes the
singles as MDQ-P1 words, cuts them into packets, damages the packet stream on purpose, and
sends it paced in detector time (a packet leaves when its first single has "happened") or as
fast as possible. The damage is reproducible for a given seed:

```{.cpp include="minidaq/include/minidaq/sim/readout_link.hpp" snippet="faults"}
```

Because the injector reports exactly what it did, the tests can demand exact agreement: in
`AccountsForEveryPacketThroughAFaultyLink`, 2,000 packets cross a link with 1% loss, 2%
reordering and 0.5% duplication, and the tracker's lost count equals the injected losses,
its stale count equals the injected duplicates, and the delivered words are in order.

### Measured on the loopback interface

The script `measurements/ch09/udp_runs.py` runs `minidaq_server` with a UDP source and sends
one simulated second with `minidaq_send` for each scenario. The brain phantom of Chapter 8 at
2 MBq produces 895,956 singles in that second, 4,923 packets of up to 182 words. At 5 MBq it
produces 2,236,860 singles in 12,291 packets. All runs are on the book's 4-vCPU virtual
machine, over the loopback interface, which has no physical link and so measures the
software, not a network.

| Scenario | Sent | Received | Delivered | Lost | Reordered | Stale |
|------------|------------:|------------:|------------:|------------:|--------------:|------------:|
| 2 MBq, clean | 4,923 | 4,923 | 4,923 | 0 | 0 | 0 |
| 2 MBq, faults, 1 ms hold | 4,927 | 4,927 | 4,920 | 3 | 5 | 7 |
| 2 MBq, faults, 5 ms hold | 4,927 | 4,927 | 4,922 | 1 | 7 | 5 |
| 5 MBq burst, 4 MiB | 12,291 | 12,291 | 12,291 | 0 | 0 | 0 |
| 5 MBq burst, 64 KiB | 12,291 | 5,037 | 5,037 | 7,090 | 0 | 0 |
| 5 MBq burst, 32 words | 69,902 | 69,902 | 69,902 | 0 | 0 | 0 |

: MiniDAQ's UDP readout on the loopback interface (measurements/ch09/udp_runs.txt). "2 MBq" runs are paced in real time; "burst" runs send as fast as possible, with the receive buffer or packet size given. Injected faults: 1 packet lost, 7 delayed by up to 8 positions, 5 duplicated.

Four results are worth reading slowly.

*The hold time is a trade-off you can measure.* With faults injected and a 1 ms hold, the
receiver counted 3 lost and 7 stale packets, against 1 injected loss and 5 duplicates. The
difference is two delayed packets that arrived more than 1 ms late: at 4,923 packets per
second, a delay of 8 positions is 1.6 ms. Their gaps were given up, so they arrived stale.
With a 5 ms hold, the counts match the injection exactly: 1 lost, 7 reordered, 5 stale.
Every packet is accounted for in both runs (the words delivered differ by exactly two
packets of 182 words); what the hold time decides is whether a late packet is used or
counted. A longer hold costs latency only when there is a gap, so it is cheap on a healthy
link.

*The receive buffer decides whether a burst survives.* At full speed the sender pushed 12,291
packets (18 MB) in 26 ms, about 470,000 packets per second. With the buffer the kernel
actually granted (4 MiB, capped by `rmem_max` from the 8 MiB requested), nothing was lost.
With 64 KiB, 7,090 packets, 58%, were counted lost, and the next result shows that even
that is not all of them.

*Loss at the end is invisible.* In the 64 KiB run, 5,037 packets were delivered and 7,090
counted lost, which leaves 164 of the 12,291 unaccounted for. They were the last packets of
the stream, the end-of-stream packet among them, and a sequence number gap that nothing
follows looks exactly like silence. Only the sender's own count reveals them. A production
system needs an end-of-run handshake, or periodic packets that carry the sender's running
count, to close that hole.

*The software keeps up with far more than one Gigabit link can carry.* Real time at 2 MBq is
58 Mbit/s. The full-speed run moved 5.6 Gbit/s through the loopback interface without loss,
but it says nothing about a real network card, its interrupt rate or its driver, which must
be measured on the target PC.

### What the measurements found

Measuring the real path found three problems that no unit test had found, which is the
argument for measuring early. (The fourth problem of this chapter, the 2^31^ jump, was found
by the fuzzer, which is the argument for fuzzing every parser and state machine that reads
from a network.)

- **A second run on the same port could not start.** The service created the new run's
  detector before releasing the previous one, and the previous one still held the UDP port.
  The simulated detector of Chapter 6 holds no exclusive resource, so the bug was invisible
  until a port was involved. The service now releases the previous run's pipeline, detector
  and sink first, and `ASecondRunOnTheSamePortStarts` keeps it that way.
- **"Reordered" counted the wrong thing.** The first version counted every packet that waited
  behind a gap, so one lost packet made 39 good ones look reordered. An operator reading that
  counter would have looked for a switch problem that did not exist. It now counts packets
  that arrived after a higher sequence number, which is what the word means.
- **The receive buffer report misled.** "8 MiB requested, 8 MiB granted" was the kernel's
  doubled value of a buffer capped at 4 MiB. The status now reports the useful size and says
  when it is smaller than requested.

::: box-mistakes
- **A blocking receive in the source thread.** A `recv` that blocks cannot see a stop request
  or expire a gap. MiniDAQ's socket is non-blocking and `read()` returns 0 when nothing is
  there; the pipeline's back-off does the waiting.
- **One system call and one allocation per packet.** At 50,000 packets per second both show
  up in a profile. Receive in batches (`recvmmsg`) into buffers allocated once.
- **Trusting the configuration for the socket buffer.** Read back what the kernel granted, and
  check the operating system's own counter of datagrams dropped for a full buffer (the
  `RcvbufErrors` field of the `Udp` lines in `/proc/net/snmp`, or `netstat -su`) during
  acceptance tests.
- **Measuring only on loopback.** It measures the software. A real NIC adds interrupts,
  driver queues and its own drop counters; measure on the target PC with the real link
  before claiming a rate.
:::

::: box-regulated
A readout link is where data integrity, cybersecurity and SOUP meet.

- **Data integrity is a requirement, with tests.** "Every packet is delivered, counted as
  lost, counted as stale or rejected with a reason" is a software requirement
  (SRS-RDO-007 in MiniDAQ's tests), and the counters are the evidence that it holds in a
  given acquisition. Whether lost data can affect a clinical result is a hazard for the risk
  analysis (ISO 14971, Chapter 15), and the loss counters and any threshold that faults a run
  are its risk controls.
- **The list-mode file must carry the link counters** (Chapter 12), so that an analysis or a
  complaint investigation can tell a run with loss from a clean one without the DAQ's logs.
- **An open UDP port accepts datagrams from anyone who can reach it.** MDQ-R1 has no
  authentication. That is acceptable only on a dedicated, physically separated readout
  network, and the threat model (IEC 81001-5-1, Chapter 17) must say so, together with what
  happens when the assumption fails: the magic, version and length checks reject garbage,
  the counters show it, and nothing in the packet can make the receiver read out of bounds.
- **The operating system's network stack is SOUP.** Its configuration (`rmem_max`, interrupt
  affinity, the NIC's ring sizes) is part of the system's configuration and belongs in the
  installation and verification records, not in someone's memory.
:::

::: box-askteam
1. Where is the specification of the event words and packets that your scanner's readout
   sends, which version is current, and who approves changes to it?
2. Which link carries the data from the detector to the acquisition PC (Ethernet, PCIe,
   optical), at what bandwidth, and is the network dedicated to it?
3. How are the boards' clocks distributed and synchronized? How is a loss of
   synchronization detected, and what does the DAQ do about it?
4. How does the current DAQ detect and report lost data, and what loss rate, if any, has been
   accepted for a clinical acquisition?
5. Which fine-time, walk and energy calibrations does the firmware apply, and which does the
   software apply? Where are the calibration tables stored, and how is their version recorded
   with the data?
:::

## Exercises {.unnumbered}

**Exercise 9.1 (M): Decoding a TDC word with rollover.** *Goal:* write a decoder for a
made-up 64-bit word with a 4-bit type, a 10-bit channel, a 40-bit coarse time (5.12 ns ticks)
and a 10-bit fine time (5 ps bins), returning absolute times across the 94-minute rollover
while words arrive a few microseconds out of order. *Starter:* `exercises/ch09/e1_tdc_word/`
(treats every word as a hit; takes any step back for a wrap). *Acceptance:*
`tests/test_tdc_word.cpp` passes: units, no overflow at the largest code, other word types
skipped and counted, a wrap undone exactly, a late word not taken for a wrap on either side
of a wrap, 2.9 hours of data monotonic with one wrap. *Time:* 1.5 hours.

**Exercise 9.2 (M): Counting loss and reordering on a link.** *Goal:* a monitor that counts
lost, reordered and duplicated packets from a board's 16-bit sequence numbers without holding
any packets, checked against MiniDAQ's fault injector at 0.1% loss and 0.2% reordering.
*Starter:* `exercises/ch09/e2_link_monitor/` (an unsigned gap, no memory of what was seen).
*Acceptance:* `tests/test_link_monitor.cpp` passes: hand-made cases including the wrap from
65,535 to 0, and exact agreement with the injected losses, delays and duplicates over 200,000
packets. *Time:* 1.5 hours.

**Exercise 9.3 (H): Two boards, 20 ppm apart.** *Goal:* correct two drifting board clocks
to global time from periodic sync pulses, and estimate the relative drift from the
coincidences alone. *Starter:* `exercises/ch09/e3_clock_drift/` (a working simulator, a
correction that removes only the offset, an estimate that returns 0). *Acceptance:*
`tests/test_clock_drift.cpp` passes: residuals within 5 ps with exact sync stamps; with
100 ps photon jitter, a mean within 5 ps and a spread between 130 and 160 ps; one sync per
second enough for constant drift (mean within 60 ps); the drift from the data within 0.05 ppm. *Time:* 2.5 hours.

**Exercise 9.4 (E, extra): Time walk and time over threshold.** *Goal:* on a model
scintillator pulse, measure leading-edge walk, show that constant-fraction timing removes it,
and show that time over threshold is logarithmic in energy. *Starter:*
`exercises/ch09/e4_time_walk/` (Python; a 50 ps scan, constant fraction and ToT missing).
*Acceptance:* `tests/test_time_walk.py` passes: crossings exact to 1 µV, walk over 20 ps at
100 keV, constant-fraction walk under 0.01 ps, 27.7 ns of ToT per doubling within 2%.
*Time:* 45 minutes.

**Exercise 9.5 (E, extra): A link budget.** *Goal:* how many singles per second fit on
Gigabit and 10-Gigabit Ethernet in MDQ-R1 packets, counting every byte of wire time, and what
small packets cost. *Starter:* `exercises/ch09/e5_link_budget/` (Python; counts only payload,
IP and UDP). *Acceptance:* `tests/test_link_budget.py` passes: 1,538 wire bytes for a full
packet, the 84-byte minimum, 14.8 M singles/s per Gigabit link at 182 words per packet and
11.8 M at 32, 67.6% utilization at 10 M singles/s. *Time:* 30 minutes.

## MiniDAQ milestone: the UDP readout link {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ acquires from a UDP readout link: packets with sequence numbers, restored to
order within a window, every packet delivered or counted, link counters in the status report,
and a sender that plays the detector with reproducible faults. **Start:** tag `ch08`.
**End:** tag `ch09`.
:::

1. Add `minidaq/include/minidaq/format/readout_packet.hpp` and `.cpp`: the MDQ-R1 header,
   `encode_packet`, `parse_packet`, serial arithmetic and `SequenceTracker`, with
   `test_readout_packet.cpp`.
2. Add `sim::Packetizer` and `sim::LinkFaults` (`sim/readout_link.hpp` and `.cpp`).
3. Add `control::UdpDetector` (`control/udp_detector.hpp` and `.cpp`) and select it in
   `make_default_detector` for source type `"udp"`; add `DetectorPort::counters()` and copy
   the counters into the status report.
4. Extend the configuration to schema 1.1 (`source.type`, `source.udp`), the JSON Schema
   document and the configuration tests; make the schema test walk nested objects.
5. Add `test_udp_detector.cpp`: open errors, exact accounting over the loopback interface, a
   full acquisition through the service, and a second run on the same port.
6. Add the tool `minidaq_send`, the configuration `minidaq/configs/udp-loopback.json` and the
   measurement script `measurements/ch09/udp_runs.py` with its results.

**Definition of done.** `ci/run_all.sh` is green on all six presets; `tools/static_analysis.sh`
reports nothing; `architecture.layers` passes (the tracker is in the core layer, the socket
only in the adapters layer); `minidaq_send --activity 2e6 --seconds 1 --loss 0.001 --reorder
0.001` into a running server with a 5 ms hold time gives link counters that match the
sender's injected faults exactly. Tag `ch09`.

## Check yourself {.unnumbered}

1. What happens to your sorter if one board's clock drifts by 1 ns per second? How would you
   detect it from the data alone?
2. A 50-bit time code in 5 ps units wraps every 94 minutes. Why is that more dangerous than a
   counter that wraps every second?
3. State the half-range rule for unwrapping a counter, and say what goes wrong with "a step
   back is a wrap".
4. Why does a fixed-threshold trigger produce an energy-dependent time error, and name two
   ways to remove it.
5. Why is time over threshold a nonlinear measure of energy, and what does that mean for an
   energy window?
6. Why do readout links use UDP rather than TCP, and what must the receiver do in exchange?
7. A packet with sequence number 2 arrives after packet 5 on a link whose tracker has given
   up on the gap at 2. What does the tracker do with it, and why?
8. Your link carries 10 M singles/s in 182-word packets on Gigabit Ethernet. How full is it,
   and what changes if the firmware switches to 32-word packets?
9. The kernel reports an 8 MiB receive buffer after you asked for 8 MiB. How large is the
   buffer for data, and how do you find out whether it was capped?
10. Which failure of a readout link do sequence numbers not reveal, and how do you close that
    gap?
11. Name the checks a parser for a hardware packet must make before it reads the first data
    word.

## Summary {.unnumbered}

- A front end reduces each photodetector pulse to a time stamp and an energy; leading-edge
  timing walks with energy, constant fraction does not, and ToT energy is logarithmic.
- Time stamps are a coarse count plus a fine interpolation that needs calibration; counters
  wrap, and the half-range rule unwraps them even when words arrive late.
- Boards must count the same time: a common clock or a synchronization protocol, plus
  monitoring of the coincidence time peak to detect when that fails.
- A hardware specification must state bit numbering, byte order, units, word types, reserved
  bits, versioning and ordering; decode with shifts and masks and check every field.
- Readout links use UDP: no retransmission, so loss is made visible with sequence numbers and
  serial arithmetic instead.
- Budget a link in bytes and in packets per second; Ethernet, IPv4 and UDP add 66 bytes of
  wire time per frame.
- MiniDAQ's tracker restores order within a window and a hold time, and counts every packet as
  delivered, lost, stale or rejected; the counters reach the operator in the status report.
- Measure the real path early: the loopback measurements found three bugs that unit tests had
  not.

## Further reading {.unnumbered}

- R. Bugalho et al., "Experimental characterization of the TOFPET2 ASIC", *Journal of
  Instrumentation* 14 (2019) P03029.
- R. Lecomte, "Novel detector technology for clinical PET", *European Journal of Nuclear
  Medicine and Molecular Imaging* 36 Suppl 1 (2009) S69–S85.
- D. R. Schaart, "Physics and technology of time-of-flight PET detectors", *Physics in
  Medicine and Biology* 66 (2021) 09TR01.
- S. Gundacker et al., "Experimental time resolution limits of modern SiPMs and TOF-PET
  detectors exploring different scintillators and Cherenkov emission", *Physics in Medicine
  and Biology* 65 (2020) 025001.
- J. Postel, "User Datagram Protocol", RFC 768, 1980; R. Elz, R. Bush, "Serial Number
  Arithmetic", RFC 1982, 1996.
- W. R. Stevens, B. Fenner, A. M. Rudoff, *UNIX Network Programming, Volume 1: The Sockets
  Networking API*, 3rd ed., Addison-Wesley, 2004.
- The Linux manual pages socket(7), udp(7) and recvmmsg(2): the receive buffer, its limits
  and the doubling.
- J. Serrano et al., "The White Rabbit project", Proceedings of ICALEPCS 2009, Kobe (verify:
  the citation details).
