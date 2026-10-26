# Exercise 23.1 (E): Where did the datagrams go?

**Goal.** Write the drop report an engineer makes after a run with loss: read the host's counters
before and after, and say at which layer of the receive path datagrams were dropped. It is the
first thing to do when a run's `packets_lost` is not zero, before anyone changes a buffer size or
blames the network.

**Time.** 45 minutes.

**The files** (Chapter 23 shows each one):

- `/proc/net/snmp`: two `Udp:` lines, the names and then the values. `RcvbufErrors` counts the
  datagrams dropped because a socket's receive buffer was full, for every socket of the host.
- `/proc/net/softnet_stat`: one line per CPU, hexadecimal. The first column is the packets
  processed, the second the packets dropped because the CPU's backlog was full, the third the
  times the receive softirq ran out of budget (`time_squeeze`). They are 32-bit and wrap.
- `/proc/net/udp`: one line per socket. The tenth field is the inode, the thirteenth the drops of
  that socket, a 32-bit counter.
- `/sys/class/net/IF/statistics/`: the network card's counters, one file each.

**Starter.** `starter/where_dropped.py`: four functions to write.

**Tasks.**
1. `parse_snmp_udp`, `parse_softnet` and `socket_drops`: the parsers, with the errors their
   docstrings ask for.
2. `report(before, after, inode)`: the drops of each layer between the two snapshots, the drops of
   the host's other sockets, and the verdict: the first layer, in the order a datagram meets them
   (card, backlog, socket buffers), that dropped anything.

**Acceptance** (`ch23/e1_where_dropped/<variant>/unittest`): the tests pass, including counters
that wrap, a column order that differs from the usual one, and a layer that cannot be read, which
is reported as unknown rather than zero.

**Then** answer in `NOTES.md`: why is the verdict the *first* layer with drops, and not the layer
with the most?
