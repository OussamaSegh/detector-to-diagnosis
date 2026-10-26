# High-throughput networking {#ch23}

::: box-why
Chapter 9 built MiniDAQ's readout link and measured it on the loopback interface, and one result
was left open: the last packets of a burst could disappear without any counter saying so. On a
scanner, the link is a 10-Gigabit network card, a driver, interrupts, a softirq, the IP and UDP
layers and a socket, and a datagram can be dropped in each of them, each time for another reason
and with another counter. When a run's numbers are wrong, the engineer who can say *where* the
data was lost fixes it in an hour; the one who cannot raises every buffer and hopes. This chapter
follows a datagram from the wire to `read()`, names every queue it waits in, the counter that
records its loss there and the setting that sizes it; makes MiniDAQ count the drops at its own
socket, including the last ones of a run; sizes a receive buffer from a measured footprint
instead of a guess; measures what receiving costs; and decides, with numbers, when bypassing the
kernel would be worth what it costs.
:::

**A day in the life.** It is the second day of the acceptance tests of a new scanner, and the
count-rate test at the highest activity is 3% short of the reference. Every run is marked complete:
`packets_lost` is zero, nothing is stale, no fault. The physicist suspects the dead-time model.
You ask for the run records and for the output of `netstat -su` before and after a run, and the
second shows 2,041 more `receive buffer errors` than the first. Each acquisition ends with a stop,
and at the stop the boards flush their FIFOs: tens of milliseconds of data in a few milliseconds.
The receive buffer, sized for the steady rate, overflowed, and the datagrams it dropped were the
last of the run, so no later sequence number ever showed a gap. The data loss was real and the
software's verdict was wrong. By the afternoon you have two changes: MiniDAQ asks the kernel for
its socket's drops and counts them in the verdict, and the receive buffer is sized for the flush,
not for the average. The count-rate test passes the next morning.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Follow a UDP datagram through the Linux receive path (card, ring, softirq, backlog, IP and UDP,
   socket buffer, application) and name the queue, the counter and the setting at each step.
2. Find where datagrams were dropped from the host's own counters (`/proc/net/snmp`,
   `/proc/net/softnet_stat`, `/proc/net/udp`, the card's statistics) and tell a loss on the
   network from a loss in the PC.
3. Count the drops at your own socket with `SO_RXQ_OVFL` and `/proc/net/udp`, including those
   after the last datagram, and make them part of a run's integrity verdict.
4. Size a socket's receive buffer from the bytes the kernel charges per datagram and the longest
   burst and stall it must survive, and check the host allows it.
5. Measure the cost of receiving, and explain when batched receives, larger datagrams, interrupt
   affinity and busy polling help.
6. Decide, with criteria, when kernel bypass (AF_XDP, DPDK) is worth its cost in a regulated
   product.

## Prerequisites and estimated time {.unnumbered}

Chapter 4 (scheduling and latency), Chapter 5 (measuring performance), Chapter 9 (the readout
link and MDQ-R1), Chapter 15 (the fault tree of H-01) and Chapter 22 (how Linux exposes
hardware). Reading: about 3 hours. Exercises: 3.5 to 4.5 hours. Milestone: 4 hours. If time is
short, do Exercises 23.1 and 23.3.

## The receive path, from the wire to `read()`

### The intuition

A datagram on its way from the wire to MiniDAQ waits in a row of queues. Each queue has a size,
someone who fills it, someone who empties it, and a counter for what did not fit. A drop happens
where the filling is faster than the emptying for longer than the queue can absorb, and the
counter of that queue is the only place where the drop is recorded. Everything in this chapter
follows from that picture: to find a loss, read the counters in the order the datagram meets the
queues; to prevent one, find the queue whose emptying stalls, and make it larger or its emptying
more regular.

| Where | Filled by | Emptied by | Counter of what did not fit | Sized by |
|---|---|---|---|---|
| Card's receive ring | the card, by DMA, as frames arrive | the driver's poll in the softirq | `rx_missed_errors`, `rx_fifo_errors` (driver names vary; `ethtool -S`) | `ethtool -G IF rx N` |
| Per-CPU backlog (with RPS, or loopback) | the softirq of the receiving CPU | the softirq of the target CPU | `/proc/net/softnet_stat`, column 2 | `net.core.netdev_max_backlog` |
| Socket's receive buffer | the softirq, after IP and UDP | your `recv` calls | `RcvbufErrors` in `/proc/net/snmp`; this socket's drops in `/proc/net/udp` | `SO_RCVBUF`, capped at `net.core.rmem_max` |
| Your pipeline | your receiving thread | your pipeline's stages | your own counters (Chapter 3) | your configuration |

: The queues of the Linux receive path, and where each records its drops.

### The card and its ring

A network card does not interrupt the CPU for every frame. The driver gives it a *ring* of
receive descriptors, each pointing to a buffer in memory; the card writes each arriving frame
into the next free buffer by DMA, marks the descriptor as used, and raises an interrupt, at most
as often as its *interrupt coalescing* settings allow (`ethtool -c`). The driver's interrupt
handler does almost nothing: it masks the card's interrupt and schedules the *NAPI* poll, which
runs in a softirq and takes frames off the ring until the ring is empty or the poll's budget is
spent. While the CPU does not run the poll, the card keeps filling the ring, and when the ring is
full the card drops frames and counts them. Ring sizes are a few hundred to a few thousand
descriptors (`ethtool -g` shows the current and the maximum); at a million frames per second, a
ring of 1,024 descriptors is one millisecond of traffic.

A card with several receive queues spreads the flows over them by a hash of their addresses and
ports (*receive side scaling*, RSS), each queue with its own interrupt, so that several CPUs can
receive at once. A readout link is usually one flow, one board's address and port to one socket,
and so lands on one queue and one CPU, whatever the card's number of queues. Several boards are
several flows and can be spread.

### The softirq and the backlog

The NAPI poll runs in the `NET_RX` softirq, on the CPU that took the interrupt. Each run of the
softirq has a budget: `net.core.netdev_budget` packets (300 by default) and
`net.core.netdev_budget_usecs` microseconds (8,000 on the book's machine). When it runs out with
packets still waiting, it gives the CPU back and counts a `time_squeeze` in the third column of
`/proc/net/softnet_stat`. A rising `time_squeeze` means the CPU that receives cannot keep up with
the card, which is a warning before the ring overflows.

With *receive packet steering* (RPS), which spreads packets over CPUs in software for cards with
one queue, and on the loopback interface, packets are handed to a CPU through a per-CPU *backlog*
of `net.core.netdev_max_backlog` packets (1,000 by default). A full backlog drops the packet and
counts it in the second column of `/proc/net/softnet_stat`.

### IP, UDP and the socket buffer

The softirq passes the packet through IP and UDP: header checks, the UDP checksum
(`InCsumErrors` when it is wrong), and the lookup of the socket bound to the destination port
(`NoPorts` when there is none; a datagram that arrives before MiniDAQ has bound its port is
counted there). Then the datagram is appended to the socket's receive queue, unless the queue is
full: that is `RcvbufErrors` in `/proc/net/snmp`, counted for the whole host, and the drops column
of the socket's own line in `/proc/net/udp`.

The size of the socket's queue is set with `SO_RCVBUF` and is not what it seems. Chapter 9 found
that the kernel caps the request at `net.core.rmem_max` without an error and stores twice the
value it grants. The second surprise is what the limit is compared with: not the payload, but
each datagram's *truesize*, the memory the kernel holds for it (the socket buffer structure and
the allocation the driver made for the frame). This chapter's measurement filled a socket that
nobody read and counted what it kept:

| Datagram | Buffer granted | Datagrams queued | Bytes charged per datagram |
|---:|---:|---:|---:|
| 1,472 B | 65,536 B | 56 | 2,341 B |
| 1,472 B | 1,048,576 B | 910 | 2,305 B |
| 1,472 B | 4,194,304 B | 3,640 | 2,305 B |
| 8,208 B | 1,048,576 B | 126 | 16,644 B |
| 8,208 B | 4,194,304 B | 504 | 16,644 B |

: How many datagrams a receive buffer holds, on the loopback interface of the book's machine (measurements/ch23/buffer_footprint.txt).

A full-size MDQ-R1 packet of 182 words is charged 2,305 bytes, 57% more than its payload. A
jumbo datagram of 1,024 words is charged twice its payload, because its allocation is rounded up
to 16 KiB. A real card's driver allocates differently (often a page or half a page per frame);
run `measurements/ch23/buffer_footprint.py` on the target PC with its card before you size a
buffer.

### The application

Last, your receiving thread takes datagrams out of the socket with `recv`, `recvmsg` or
`recvmmsg`, which copies each into your buffer and frees the kernel's memory. From then on the
datagram is your pipeline's, and your own counters account for it (Chapter 3). A receiving thread
that is not scheduled, because a higher-priority thread runs on its CPU, because the CPU is busy
with the softirq itself, or because a virtual machine's host did not run the virtual CPU, lets
the socket buffer fill. That is the most common cause of loss on a DAQ PC, and the next section
shows how to see it.

## Every drop has a counter

### The host's counters

Linux keeps the counters of the receive path in files that any user can read. They are
cumulative since boot, so what matters is the difference between two readings, one at the start
of a run and one at the end. `netstat -su` and `nstat` print them in words; a program reads the
files. `/proc/net/snmp` has a pair of lines per protocol, names and then values, and the columns
are found by name, because kernels have added columns over the years:

```{.cpp include="minidaq/src/net/host_counters.cpp" snippet="snmp"}
```

MiniDAQ's module `minidaq/net/host_counters` (core layer: it reads text and files and includes no
socket header) parses the four sources of the table above into these structures:

```{.cpp include="minidaq/include/minidaq/net/host_counters.hpp" snippet="counters"}
```

Two rules shape it. A counter that cannot be read is left out, never reported as zero, because a
zero says that nothing was dropped, which nobody measured; the parsers return nothing for a file
they do not understand, and the difference of two readings contains only the counters both
have. And the host's counters are host-wide: `RcvbufErrors` counts the drops of every socket, the
card's counters every flow. They explain a loss; they do not decide whether *this* run lost data.

### One socket's drops

For its own socket MiniDAQ has two exact sources. The first is `/proc/net/udp`, one line per UDP
socket of the host, which ends with the socket's drop count. The socket is found by its inode
number, which `fstat` on its descriptor gives:

```{.cpp include="minidaq/src/net/host_counters.cpp" snippet="proc-net-udp"}
```

The second travels with the data. With the socket option `SO_RXQ_OVFL` (socket(7), since Linux
2.6.33), the kernel attaches the socket's drop count to every datagram it queues, as a control
message that `recvmsg` and `recvmmsg` return next to the payload:

```{.cpp include="minidaq/src/control/udp_detector.cpp" snippet="rxq-ovfl"}
```

```{.cpp include="minidaq/src/control/udp_detector.cpp" snippet="dropped-so-far"}
```

Reading it costs no system call: the receive loop already has the message headers. And it says
*where* in the stream the drops happened: right before the first datagram that carries a larger
count. Its limit is in the same sentence. The count is written into a datagram when the datagram
is queued, so drops after the last datagram that is queued are carried by no datagram at all.

### The tail of a burst

That limit is the hole Chapter 9 found. A datagram that is dropped leaves a gap in the sequence
numbers only when a later datagram arrives; the last datagrams of a burst, or of a run, leave no
gap and no `SO_RXQ_OVFL` count. The UDP adapter therefore reports the larger of its two sources,
because `/proc/net/udp` has the count at any time:

```{.cpp include="minidaq/src/control/udp_detector.cpp" snippet="socket-drops"}
```

and the integrity verdict of Chapter 15 now counts `socket_drops` as a loss, next to
`packets_lost` (SRS-RDO-013, SRS-RDO-015, risk control RC-29 of H-01):

```{.cpp include="minidaq/src/control/run_integrity.cpp" snippet="assess"}
```

The measurement that decided it repeats Chapter 9's burst: one simulated second at 5 MBq, 12,291
datagrams of 182 words, sent over the loopback interface as fast as the sender can, into receive
buffers of four sizes, three times each. One of the three repetitions:

| Scenario | Buffer granted | Sent | Delivered | Lost (gaps) | Socket drops | Delivered + drops |
|---|---:|---:|---:|---:|---:|---:|
| real time, 2 MBq | 65,536 | 4,923 | 4,923 | 0 | 0 | 4,923 |
| burst, 5 MBq | 65,536 | 12,291 | 8,004 | 2,216 | 4,287 | 12,291 |
| burst, 5 MBq | 262,144 | 12,291 | 8,542 | 2,043 | 3,749 | 12,291 |
| burst, 5 MBq | 1,048,576 | 12,291 | 10,331 | 1,960 | 1,960 | 12,291 |
| burst, 5 MBq | 4,194,304 | 12,291 | 12,291 | 0 | 0 | 12,291 |
| burst, 1,024 words | 1,048,576 | 2,185 | 478 | 1,667 | 1,707 | 2,185 |

: Where the datagrams of a burst go, on the loopback interface (measurements/ch23/drop_accounting.txt, run 2 of 3). The host's RcvbufErrors equaled the socket drops in every run.

Three results matter.

*Every datagram is accounted for.* In all 18 runs, the datagrams delivered plus the socket's drops
equal the datagrams sent, exactly. On the loopback interface there is no card and no wire, so the
socket buffer is the only place a datagram can be lost, and the kernel's count is complete.

*The sequence gaps undercount, by the tail.* In the 64 KiB run, the gaps showed 2,216 lost
packets and the socket dropped 4,287: the other 2,071 were the end of the burst, after the last
datagram that was queued. Before this chapter, that run would have been judged incomplete for the
wrong number; a run whose drops were *all* at the end, which is what a flush at the stop of a run
produces, would have been judged complete.

*A buffer does not make a burst safe.* The same 4 MiB buffer that kept all 12,291 datagrams in
runs 2 and 3 dropped 180 of them in run 1 (82 in gaps, 98 in the tail), and the 1 MiB buffer
kept everything in run 1 and dropped 5,109 in run 3. The buffer's capacity is fixed; what varies
is how long the receiving thread was not reading, on a virtual machine whose four virtual CPUs
the sender, the receiver, the pipeline and the softirq share. The next section turns that into
arithmetic.

### What the counters cannot see

Loss on the network after the last datagram that reaches the host is invisible to every counter
of the host: a switch that drops the last packets of a run leaves no gap, no socket drop, no
card counter. The only remedy is the sender's own count, sent in-band (a final packet that says
how many came before it, or periodic packets that carry the running count), which is part of the
interface between the firmware and the software that Chapter 24 is about. Until then, ADR 0018
records it as a residual of H-01.

## Sizing the socket buffer

The socket buffer is where datagrams wait while the receiving thread is not reading. It must hold
everything that arrives during the longest such pause, at the rate that arrives *during* the
pause:

    capacity (datagrams) = 2 x granted / bytes charged per datagram
    longest stall        = capacity / datagram rate during the stall

With the measured 2,305 bytes per datagram, a 4 MiB buffer holds 3,639 datagrams. For Chapter 9's
real-time link at 2 MBq, 4,923 datagrams per second, that is 0.74 s of stall, far more than a
receiving thread with real-time priority waits: Chapter 4 measured a worst wake-up latency of
8.4 ms under load on the book's virtual machine, and published figures for bare metal with
`PREEMPT_RT` and isolated CPUs are tens of microseconds. For the same data sent as a burst at
470,000 datagrams per second, it is 7.7 ms, less than that worst case, which is why the bursts
above dropped data on some runs and not on others. Exercise 23.3 turns the
formulas into code, including the smallest request for a given stall.

So the question to ask is not "how large is the buffer" but "what is the longest burst, at what
rate, and what is the longest stall of the receiving thread". The firmware team knows how the
boards send: as they measure, or from a FIFO that empties in bursts, as at the end of a run. A
switch between the boards and the PC may buffer and release bursts of its own. The stall is
yours, and Chapter 4 showed how to bound it: a receiving thread with `SCHED_FIFO` priority on a
CPU that runs nothing else. MiniDAQ's receiving thread is the pipeline's source stage, which the
real-time profile of Chapter 4 already places.

The request also needs the host's permission. `net.core.rmem_max` caps every request (4 MiB on the
book's machine, 212,992 bytes on many default installations), and raising it is a platform
setting that belongs to the system's controlled configuration (Chapter 25), recorded with the
installation and verified on every start: MiniDAQ reports the granted size and warns when it is
smaller than requested (Chapter 9). A process with `CAP_NET_ADMIN` can exceed the cap with
`SO_RCVBUFFORCE`; MiniDAQ's server does not run with that capability, and should not.

## The cost of receiving

A receive costs a system call, the kernel's work of releasing the datagram's memory, and a copy
of the payload into your buffer. Chapter 9 receives with `recvmmsg`, 32 datagrams per system call,
on the reasoning that system calls are expensive. The benchmark `bm_udp_receive` measures it:
it fills a loopback socket with 128 datagrams while the timer is stopped, then drains them, with
`recv` one at a time or with `recvmmsg` in batches.

| Call | Datagram | ns per datagram (min / median / max) | Payload at the median |
|---|---:|---|---:|
| `recv` | 1,472 B | 291 / 318 / 356 | 37.0 Gbit/s |
| `recvmmsg`, 8 | 1,472 B | 272 / 302 / 403 | 39.1 Gbit/s |
| `recvmmsg`, 32 | 1,472 B | 276 / 301 / 332 | 39.1 Gbit/s |
| `recvmmsg`, 64 | 1,472 B | 266 / 320 / 365 | 36.8 Gbit/s |
| `recv` | 8,208 B | 535 / 622 / 664 | 105.5 Gbit/s |
| `recvmmsg`, 8 | 8,208 B | 504 / 638 / 770 | 103.1 Gbit/s |
| `recvmmsg`, 32 | 8,208 B | 581 / 742 / 943 | 88.6 Gbit/s |
| `recvmmsg`, 64 | 8,208 B | 611 / 741 / 844 | 88.6 Gbit/s |

: The receiving thread's cost per datagram, 10 repetitions of 128 datagrams, release build, 4 virtual CPUs at 2.1 GHz (measurements/ch23/receive_cost.txt). The kernel's work of queuing the datagrams is not included.

Batching saved about 5% for full-size MDQ-R1 packets and nothing for jumbo ones, where batches of
32 and 64 were slower: 32 buffers of 8 KiB no longer stay in the first-level cache. On this
machine a system call is cheap next to the copy and the memory management, so the per-datagram
work, not the per-call work, sets the cost. Two conclusions follow, and neither is "batching does
not matter".

*The cost is per datagram, so larger datagrams are the lever.* A 1,024-word datagram costs about
twice a 182-word one and carries 5.6 times the words: the receive costs 0.6 ns per word instead
of 1.7. On a real network the same holds for the card's interrupts and the softirq's work, which
are also per frame. Jumbo frames need every device on the path to accept them (the card, the
switch, the board's firmware), and they make each lost frame cost more data; ask before you
assume them.

*At MiniDAQ's rates, receiving is cheap.* Chapter 9's link budget gives 54,945 datagrams per
second at 10 M singles per second; at 300 ns each, the receiving thread spends 16 ms per second,
under 2% of one core. The receive stage that Chapter 5 left unmeasured is not the pipeline's
bottleneck. Batching stays, because it costs nothing and helps where system calls are expensive:
on CPUs whose security mitigations flush state on every entry to the kernel, a system call can
cost several times what it costs here (verify on the target PC with `bm_udp_receive`).

## Tuning a receive host

With the counters in place, tuning is a loop: run the highest rate the scanner produces, read the
counters in path order, change the setting of the first queue that drops, and run again. The
settings, in that order:

- **The card's ring** (`ethtool -G IF rx N`): raise it toward the maximum when
  `rx_missed_errors` or `rx_fifo_errors` grow. A larger ring absorbs longer softirq delays at the
  cost of memory and, slightly, of cache behavior.
- **Interrupt coalescing** (`ethtool -C`): fewer interrupts per second for less CPU, at the cost of
  latency. A DAQ whose latency budget is in milliseconds (Chapter 4) can afford tens of
  microseconds of coalescing; measure the end-to-end latency after a change.
- **Interrupt affinity**: bind the card's receive interrupt to a chosen CPU
  (`/proc/irq/N/smp_affinity_list`) and keep `irqbalance` from moving it. The softirq then runs on
  that CPU. Whether the receiving thread should share that CPU (warm caches) or use a neighbor
  (no competition with the softirq) depends on the load; measure both. Keep both off the CPUs that
  Chapter 4 isolated for the pipeline's other stages.
- **The softirq's budget** (`netdev_budget`, `netdev_budget_usecs`): raise it when `time_squeeze`
  grows and the CPU has room.
- **The socket buffer** (`SO_RCVBUF`, `rmem_max`): sized as in the previous section.
- **Busy polling** (`SO_BUSY_POLL`, `net.core.busy_read`): the receiving thread polls the card's
  queue itself instead of waiting for the softirq. It lowers latency and jitter at the price of a
  CPU that spins; worth it when latency matters more than a core, which in a PET DAQ it rarely
  does.

Every one of these settings is a property of the installed system, not of MiniDAQ's code: it
belongs in the platform's configuration, applied by the image (Chapter 25), recorded with the
installation, and checked at start. A tuning that lives in an engineer's shell history is lost at
the first reinstallation, and the counters will say so only after a patient's scan.

::: box-mistakes
- **Raising every buffer at once.** It hides the queue that actually overflowed and wastes memory
  in the others. Read the counters in path order and change one setting at a time.
- **Trusting `packets_lost == 0`.** The sequence gaps miss the last datagrams of a burst. Count the
  socket's drops too, and judge runs by the integrity verdict.
- **Sizing for the average rate.** The buffer must hold the burst. Ask how the boards send, and size
  for the flush at the end of a run, not for the steady rate in the middle.
- **Sizing with the payload.** The kernel charges truesize: 2,305 bytes for a 1,472-byte datagram
  on loopback, other amounts on other drivers. Measure it on the target.
- **Reporting an unreadable counter as zero.** A zero is a claim that nothing was dropped.
- **Tuning by hand on the installed system.** Settings that are not in the platform's configuration
  disappear with the next update.
:::

## Kernel bypass, and when it is worth its cost

Everything above keeps the kernel's network stack. The alternative is to bypass it: let the
application take frames from the card's ring directly, without the softirq, the socket and the
copy. Two forms are common on Linux:

- **AF_XDP** (in the kernel since 4.18): an XDP program, a small verified program that runs in the
  driver for every frame, redirects the readout flow to a socket that shares a memory region with
  the application. Other traffic continues through the normal stack. It needs a driver with XDP
  support for full speed, and the application manages the frames' memory itself.
- **DPDK**: a user-space framework whose drivers take the card (or some of its queues) away from
  the kernel and poll it from dedicated cores. It reaches the highest packet rates and needs the
  most: a supported card, hugepages, cores that spin at 100%, and its own tools in place of the
  kernel's.

What they give is packet rate: millions of packets per second per core, where the kernel's stack
manages perhaps one to a few million with careful tuning (verify on the target). What they cost
is everything this chapter relied on: the kernel's counters, `tcpdump`, the socket's accounting,
and a stack that every Linux distribution maintains and patches. In a regulated product they also
move the receive path from platform SOUP into code and SOUP that you maintain, verify and keep
patched for the product's lifetime (Chapters 7 and 17).

MiniDAQ's decision is ADR 0018: no kernel bypass now. At the rates this project acquires, the
measured receive cost is under 2% of a core, and every drop the measurements found was at the
socket buffer, where the remedy is a buffer sized for the burst and a receiving thread that is
scheduled in time. The ADR states the evidence that would reopen it: a measurement on the target
PC, with its card, at the scanner's highest rate, that shows the receive path using more than a
quarter of a core, or drops at the card or the backlog that tuning does not remove.

::: box-regulated
- **Data integrity needs a complete account.** The integrity verdict is a risk control of H-01
  (Chapter 15). A verdict that counts gaps but not tail drops has a loss path without a counter,
  which is event E6 of the fault tree; RC-29 closes the part of it that the host can see, and
  ADR 0018 records the residual (loss on the network after the last datagram) until the interface
  with the firmware closes it.
- **The host's network settings are configuration items.** `rmem_max`, ring sizes, interrupt
  affinity and coalescing change whether data is lost. They belong in the platform configuration
  with a version, are verified at installation (the status reports the granted buffer), and a
  change to them is a change to the system, assessed like a software change.
- **The kernel's counters are evidence from SOUP.** Their formats are tested with captured text,
  and an unreadable counter is reported as unknown. When the kernel is updated, the tests of the
  parsers are part of the platform's regression tests.
- **Measurements on loopback are not verification of the product.** They verify the software. The
  receive path of the product, with its card, driver and switch, is verified on the target system
  at the highest rate the scanner produces, with the counters as the acceptance evidence.
:::

::: box-askteam
1. How do the boards send their data: as they measure, or from FIFOs that empty in bursts? How long
   and how fast is the largest burst, for example at the end of a run?
2. Which network card, driver and switch carry the readout? Does the network support jumbo frames,
   and do the boards use them?
3. Which receive buffer, ring size, interrupt affinity and coalescing does the installed system
   use, and where are those settings defined and recorded?
4. Does the current DAQ count drops at its socket and on the host, or only sequence gaps? Has a run
   ever been judged complete with drops at its end?
5. Does the firmware send its own count of the packets it sent, so that loss on the network after
   the last packet can be detected?
6. Has kernel bypass been considered, and with which measurements was it decided?
:::

## Exercises {.unnumbered}

**Exercise 23.1 (E): Where did the datagrams go?** *Goal:* from two readings of the host's counters,
before and after a run, report the drops of each layer of the receive path and the first layer that
dropped anything. *Starter:* `exercises/ch23/e1_where_dropped/starter/where_dropped.py`.
*Acceptance:* `tests/test_where_dropped.py` passes: columns found by name, counters that wrap at
2^32^, a socket found by its inode, the drops of the host's other sockets, and a layer that cannot
be read reported as unknown. Then answer in `NOTES.md` why the verdict is the first layer with drops
and not the layer with the most. *Time:* 45 minutes.

**Exercise 23.2 (M): Read the kernel's drop count.** *Goal:* read `SO_RXQ_OVFL` from the control
messages of a received datagram and turn the 32-bit cumulative count into drops since the socket
was created. *Starter:* `exercises/ch23/e2_rxq_ovfl/starter/rxq_ovfl.cpp`. *Acceptance:*
`tests/test_rxq_ovfl.cpp` passes: control messages built by hand (another type, another level, a
truncated buffer), the count's wrap, and a real socket whose buffer overflows, where the drops
arrive with the next datagram and only then. Then answer in `NOTES.md` why the first datagrams
carry no drops and what MiniDAQ does about the last ones of a run. *Time:* 45 minutes.

**Exercise 23.3 (E): Size a receive buffer.** *Goal:* compute the capacity of a receive buffer
from the bytes the kernel charges per datagram, the longest stall it survives, and the smallest
request for a given stall. *Starter:* `exercises/ch23/e3_buffer_sizing/starter/buffer_sizing.cpp`.
*Acceptance:* `tests/test_buffer_sizing.cpp` passes with this chapter's measured capacities and
stalls. Then answer in `NOTES.md` which rate you size the buffer for on a real scanner. *Time:* 30
minutes.

**Exercise 23.4 (H): A batch receiver.** *Goal:* write a receive loop with `recvmmsg` into buffers
allocated once, that recognizes a datagram that is too long, keeps the kernel's drop count of each
datagram, and keeps the error of a failed receive. *Starter:*
`exercises/ch23/e4_batch_receiver/starter/batch_receiver.cpp`. *Acceptance:*
`tests/test_batch_receiver.cpp` passes over the loopback interface: 100 datagrams in batches of
32, 32, 32 and 4, reused buffers, a datagram one byte too long, the drop count, and `EBADF`. Then
answer in `NOTES.md` why batching saved so little in this chapter's measurement, and when it would
save more. *Time:* 90 minutes.

## MiniDAQ milestone: every drop is counted {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ counts the datagrams dropped at its socket, including those after the last
datagram of a run, and its integrity verdict counts them as a loss; its status reports the host's
and the network card's drop counters since the run began; the receive buffer's size and the
receive cost are measured, and the decision about kernel bypass is recorded with its evidence.
**Start:** tag `ch22`. **End:** tag `ch23`.
:::

1. Write change request CR-0009 and ADR 0018; add SRS-RDO-013 to SRS-RDO-015 (SRS version 12) and
   risk control RC-29 of H-01; update the architecture description (version 9).
2. Add `minidaq/net/host_counters` with its tests on captured text and a fake root directory; map
   `net/` to the core layer and to the item `readout`.
3. Enable `SO_RXQ_OVFL` in the UDP adapter, read the count of every datagram, find the socket in
   `/proc/net/udp` by its inode, and report `socket_drops`, `socket_queue_bytes` and the host's
   counters; count `socket_drops` in the integrity verdict.
4. Add the adapter's tests on the loopback interface: the tail of a burst, the count that arrives
   with the next datagram, and the host's counters from a fake root.
5. Add the benchmark `bm_udp_receive` and the measurements `measurements/ch23/` (buffer footprint,
   drop accounting, receive cost).
6. Add Exercises 23.1 to 23.4.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the trace matrix shows SRS-RDO-013 to SRS-RDO-015 tested; the drop accounting shows every
datagram delivered or counted in every run; every starter of the chapter fails. Tag `ch23`.

## Check yourself {.unnumbered}

1. Name the queues a UDP datagram waits in between the wire and `recv`, and the counter that
   records a drop in each.
2. `time_squeeze` grows during a run, and nothing is dropped yet. What does it tell you, and which
   counter will grow next if nothing changes?
3. Why does a readout link from one board land on one receive queue of a card with sixteen?
4. A run's `packets_lost` is 0 and `socket_drops` is 1,500. How can that be, and was data lost?
5. `packets_lost` is 40 and `socket_drops` is 0. Where were the packets lost, or what else can
   explain the gap?
6. Why does MiniDAQ read both `SO_RXQ_OVFL` and `/proc/net/udp`? What does each give that the
   other does not?
7. Why is `RcvbufErrors` not part of the integrity verdict, although it counts the same kind of
   drop as `socket_drops`?
8. You request 8 MiB with `SO_RCVBUF` and `getsockopt` returns 8,388,608. How much data can the
   socket hold, and why may it be much less than 8 MiB of payload?
9. Boards send 4,923 datagrams per second while measuring, and flush 2,000 datagrams in 4 ms at
   the end of a run. Which buffer do you need, with 2,305 bytes charged per datagram, and what else
   must be true of the receiving thread?
10. Batching receives saved 5% here. Name two conditions under which it would save more.
11. Why are jumbo frames a bigger lever than batching, and what must be true of the network to use
    them?
12. Which evidence would make you reconsider kernel bypass for a PET DAQ, and what would it cost in
    a regulated product?

## Summary {.unnumbered}

- A datagram waits in the card's ring, possibly a per-CPU backlog, and the socket's receive buffer
  before your thread reads it. Each queue drops what does not fit and counts it in its own place:
  the card's statistics, `/proc/net/softnet_stat`, `/proc/net/snmp` and `/proc/net/udp`.
- Read the counters as differences over a run, in the order the datagram meets the queues, and
  fix the first queue that drops. Report an unreadable counter as unknown, never as zero.
- Sequence gaps miss the tail of a burst. MiniDAQ counts its socket's drops from `SO_RXQ_OVFL`
  and `/proc/net/udp`, and its integrity verdict counts them (SRS-RDO-013, RC-29). In 18 runs,
  every datagram sent was delivered or counted.
- The kernel charges each datagram its truesize: 2,305 bytes for 1,472 bytes of payload on
  loopback. Size the buffer for the burst rate over the longest stall, check `rmem_max`, and
  record the setting with the platform.
- Receiving cost about 300 ns per full-size datagram here, under 2% of a core at 10 M singles per
  second; batching saved 5%, larger datagrams save more. Tuning (rings, affinity, budget,
  coalescing, busy polling) follows the counters, one setting at a time.
- Kernel bypass buys packet rate with dedicated hardware, cores and SOUP; ADR 0018 declines it with
  the evidence and records what would reopen the decision.

## Further reading {.unnumbered}

- The Linux man-pages project: socket(7) (`SO_RCVBUF`, `SO_RXQ_OVFL`, `SO_BUSY_POLL`), udp(7),
  cmsg(3) and recvmmsg(2).
- The Linux kernel documentation, docs.kernel.org: "Scaling in the Linux Networking Stack" (RSS,
  RPS, RFS and XPS), "NAPI", "AF_XDP", and the `net.core` settings in "Documentation for
  /proc/sys/net/".
- J. Damato, "Monitoring and Tuning the Linux Networking Stack: Receiving Data", packagecloud blog,
  2016: the receive path through the kernel's source, with every counter. Written for kernel 3.13;
  the structure still holds.
- M. Majkowski, "How to receive a million packets per second", Cloudflare blog, 2015: receive
  queues, CPU placement and `SO_REUSEPORT`, measured.
- B. Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd edition, Addison-Wesley, 2020:
  chapter 10, Network.
- The DPDK project, *Programmer's Guide*, doc.dpdk.org: the poll-mode driver model and what it
  requires of the host.
