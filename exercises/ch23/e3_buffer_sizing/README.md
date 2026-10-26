# Exercise 23.3 (E): Size a receive buffer

**Goal.** Compute how long a socket's receive buffer lets the receiving thread stop reading before
datagrams are dropped, and the buffer that a given stall needs. The socket buffer is where a DAQ
PC's datagrams wait while the receiving thread is descheduled, and its size is a number to
calculate and record, not a default to trust.

**Time.** 30 minutes.

**What the kernel does** (Chapter 23): `SO_RCVBUF` grants the request capped at
`net.core.rmem_max`, stores twice that, and queues a datagram while the charges of the datagrams
already queued are below the stored value. A datagram is charged its *truesize*, not its payload:
Chapter 23 measured 2,305 bytes for a 1,472-byte datagram on the loopback interface, and 16,644
bytes for an 8,208-byte one. A real network card's driver charges differently; measure it there
with `measurements/ch23/buffer_footprint.py`.

**Starter.** `starter/buffer_sizing.hpp` and `.cpp`.

**Tasks.** `granted`, `capacity`, `longest_stall_s` and `request_for`, as their comments say.

**Acceptance** (`ch23/e3_buffer_sizing/<variant>/...`): the capacities agree with Chapter 23's
measurements, the stalls with the chapter's arithmetic, and `request_for` returns the smallest
request that is enough.

**Then** answer in `NOTES.md`: the link is the same, 2 MBq, but Chapter 9's sender can send it in
real time (4,923 datagrams per second) or as fast as possible (about 470,000). Which number do you
size the buffer for, on a real scanner, and why?
