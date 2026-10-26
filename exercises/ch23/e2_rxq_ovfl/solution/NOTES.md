# Exercise 23.2: notes on the solution

**Why the first datagrams carry no drops.** The kernel writes the socket's drop count into a
datagram when it *queues* it. The datagrams that the test receives first were queued while the
buffer still had room, before any drop; the drops happened afterwards, to datagrams that were never
queued, so nothing carries their count until the next datagram is queued. At the end of a run there
is no next datagram, and a receiver that relies on `SO_RXQ_OVFL` alone reports zero drops for a run
whose last packets it lost.

**What MiniDAQ does.** It also reads the drops column of `/proc/net/udp` for its own socket, found
by the socket's inode, which has the count at any time, and reports the larger of the two
(`socket_drops`, SRS-RDO-013). The ancillary data stays useful: it says *where* in the stream the
drops happened (right before the datagram that carries a larger count), which a total cannot.

**Why `memcpy`.** `CMSG_DATA` points just after the `cmsghdr`, which is aligned for `cmsghdr` and
not necessarily for the payload's type. Reading a `uint32_t` through a cast pointer is undefined
behavior where it is misaligned, and on some architectures it traps.

**Why the wrap needs no code.** Subtraction of unsigned 32-bit values is modulo 2^32, so
`cumulative - last` is right across the wrap as long as fewer than 2^32 drops happen between two
datagrams, which at any real rate is true.
