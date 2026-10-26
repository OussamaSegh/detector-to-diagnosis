# 0018. Kernel UDP sockets with full drop accounting, and no kernel bypass until a measurement asks for it

Date: 2026-10-26
Status: Accepted

## Context

MiniDAQ receives its data as UDP datagrams through the Linux network stack (Chapter 9, ADR 0010
for the packet format). Between the wire and MiniDAQ, a datagram can be dropped at four places: the
network card's receive ring, the per-CPU backlog of the receive softirq, the socket's receive
buffer, and, once MiniDAQ has it, the pipeline. Chapter 9 counted only what the sequence numbers
show, and its measurements found the hole in that: a datagram dropped after the last one that
arrives leaves no gap, so the last packets of a burst can disappear without a counter (fault tree
of H-01, event E6).

Chapter 23 measured where the packets of a burst go on the book's virtual machine
(`measurements/ch23/drop_accounting.txt`): in 18 runs out of 18, every datagram sent was either
delivered or counted by the kernel as dropped at MiniDAQ's socket, while the sequence gaps
undercounted the loss by up to 2,071 packets (the tail). It also measured the cost of receiving
(`measurements/ch23/receive_cost.txt`): about 300 ns per 1,472-byte datagram, with `recvmmsg`
batches 5% cheaper than one `recv` per datagram, and about 620 ns per 8,208-byte datagram, where
batching did not help. At the 2 MBq rate of Chapter 9 (4,923 packets per second) that is about
1.5 ms of one core per second.

Two questions follow: how MiniDAQ should see the drops it cannot see today, and whether it should
leave the kernel's network stack for a kernel-bypass receive path.

## Options

1. **Keep counting sequence gaps only.** No change; the tail of a burst stays invisible, and an
   operator cannot tell a network that lost packets from a PC that could not keep up.
2. **Ask the kernel.** `SO_RXQ_OVFL` attaches the socket's drop count to every datagram; the drops
   column of `/proc/net/udp` has the same count at any time, including after the last datagram; the
   host's UDP, softnet and network card counters say where else datagrams went. All are read-only,
   cost nothing on the data path, and exist on every Linux the project supports.
3. **Kernel bypass**: AF_XDP sockets (in Linux since 4.18) or DPDK, which hand the card's rings to
   the application. They remove the copies and the per-packet stack processing and can reach
   millions of packets per second per core; they also need a dedicated network card or queue, a
   polling core, a driver that supports them, and their own counters, and they move the receive path
   from SOUP that every Linux distribution maintains into code and SOUP that the project maintains.

## Decision

Option 2. The UDP adapter enables `SO_RXQ_OVFL`, reads its socket's drops from `/proc/net/udp`, and
reports the larger of the two as `socket_drops`; the run integrity verdict counts a nonzero value
as a loss (SRS-RDO-013, SRS-RDO-015, RC-29). The host's counters are reported as changes since the
run began (`host_udp_*`, `host_softnet_*`, and `nic_*` when the receiving interface is known,
SRS-RDO-014); they are host-wide, so they explain a loss but do not decide the verdict.

No kernel bypass. The measured receive cost is a small fraction of a core at the rates this
project acquires, and every drop the measurements found was at the socket buffer, where the remedy
is a larger buffer (`net.core.rmem_max`) and a receiving thread that is scheduled in time
(Chapter 4), not a different stack.

## Consequences

### Positive

- The tail of a burst is no longer silent: a run whose last packets were dropped at the socket is
  incomplete, with the count in its integrity verdict and run record.
- Network loss and host loss are told apart: `packets_lost` greater than `socket_drops` means
  packets were lost before they reached the host (or arrived too late, which `packets_stale`
  shows); `socket_drops` greater than `packets_lost` means the last ones were dropped here.
- No new SOUP, no dedicated card or polling core, and nothing on the data path but reading the
  ancillary data that comes with each datagram.

### Negative

- Loss on the network after the last datagram that reaches the host is still invisible to the
  receiver; closing it needs the sender's own count, which is part of the interface with the
  firmware (Chapter 24).
- The host's counters depend on the formats of files in `/proc` and `/sys`, which the kernel can
  change; the parsers find columns by name where the file has names, and leave out a counter they
  cannot read.
- The decision is revisited when a measurement on the target PC with its real network card shows
  the receive path using more than a quarter of a core at the scanner's highest rate, or drops at
  the card or the backlog that tuning (ring sizes, interrupt affinity, `netdev_budget`) does not
  remove. The numbers here are from loopback on a virtual machine and say nothing about a card's
  interrupts or driver (verify on the target PC).
