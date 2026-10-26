# Exercise 23.2 (M): Read the kernel's drop count

**Goal.** Read the number of datagrams a socket has dropped from the ancillary data the kernel
attaches to each datagram (`SO_RXQ_OVFL`, socket(7)), and turn the 32-bit cumulative count into
drops since the socket was created. With it, a receiver tells drops at its own socket from loss on
the network.

**Time.** 45 minutes.

**What you need.** `recvmsg` and `recvmmsg` return control messages in `msg_control`. Walk them with
`CMSG_FIRSTHDR` and `CMSG_NXTHDR` (cmsg(3)); a control message with level `SOL_SOCKET` and type
`SO_RXQ_OVFL` carries a `uint32_t`, the drops of the socket when this datagram was queued. Copy it
out with `memcpy`, because `CMSG_DATA` is not guaranteed to be aligned for the type. If the control
buffer was too small, the kernel sets `MSG_CTRUNC` in `msg_flags`.

**Starter.** `starter/rxq_ovfl.hpp` and `.cpp`.

**Tasks.**
1. `rxq_ovfl(msghdr)`: the value, or empty.
2. `DropCounter::observe`: the drops since the previous datagram and the running total, across the
   count's wrap.

**Acceptance** (`ch23/e2_rxq_ovfl/<variant>/...`): control messages built by hand (other types,
another level, a truncated buffer, none), the wrap, and a real socket on the loopback interface
whose buffer overflows: the drops arrive with the next datagram, and only then.

**Then** answer in `NOTES.md`: the test's first `receive_all` sees no drops although 20 minus
`first` datagrams were dropped. Why, and what does MiniDAQ do so that a run's last drops are
counted anyway?
