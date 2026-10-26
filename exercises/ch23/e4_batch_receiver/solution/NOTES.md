# Exercise 23.4: notes on the solution

**Why batching saved so little.** A system call costs its entry and exit, and a receive costs the
copy of the datagram and the kernel's work on its socket buffer. On the book's virtual machine the
first is small next to the second: about 300 ns per 1,472-byte datagram in total, of which batching
removed about 17 ns. For 8,208-byte datagrams the copy dominates even more, and batches of 32 and
64 were *slower*, because 32 buffers of 8 KiB do not stay in the first-level cache. Batching pays
more where a system call is expensive: on CPUs whose security mitigations flush state on every
kernel entry, with small datagrams, and at rates where one core is close to full. Measure on the
target PC (`bm_udp_receive`) before deciding.

**Why the extra byte.** UDP does not tell you a datagram's length before you receive it, and a
receive into a short buffer silently drops the rest. `MSG_TRUNC` in `msg_flags` says it happened;
the extra byte makes it impossible to miss even where the flag is not checked, because a datagram
of exactly the buffer's size is then too long by definition.

**Why errors are kept, not thrown.** The receive loop runs on the data path, where an exception's
cost and its unwinding through the pipeline are not wanted, and where `EAGAIN` is the normal case.
MiniDAQ's adapter does the same: it keeps `errno` and reports it as the adapter's fault, which the
service's monitor turns into a stopped run (Chapter 9).
