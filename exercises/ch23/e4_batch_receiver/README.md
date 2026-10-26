# Exercise 23.4 (H): A batch receiver

**Goal.** Write the receive loop of a DAQ's network input: `recvmmsg` into buffers allocated once,
datagrams that are too long recognized as such, the kernel's drop count kept with each datagram,
and errors kept for the caller instead of thrown on the data path.

**Time.** 90 minutes.

**What you need.** `recvmmsg(2)` fills an array of `mmsghdr`, each with its own `msghdr` and the
length received in `msg_len`. The kernel writes `msg_len`, `msg_flags` and `msg_controllen` back,
so set the headers up again before every call. A UDP datagram longer than its buffer is cut, and
the rest is lost; give each buffer one byte more than the largest datagram you accept, so that a
datagram that fills it is known to be too long. `MSG_DONTWAIT` makes the call return at once when
nothing is queued (`EAGAIN`), which is not an error.

**Starter.** `starter/batch_receiver.hpp` and `.cpp`.

**Tasks.** The constructor, `receive`, `datagram`, `truncated` and `drops_when_queued`, as the
header's comments say.

**Acceptance** (`ch23/e4_batch_receiver/<variant>/...`): 100 queued datagrams arrive in batches of
32, 32, 32 and 4, in order and intact; the buffers are reused; a datagram one byte too long is
flagged; the drop count arrives with the next datagram; a failed receive keeps its `errno`.

**Then** answer in `NOTES.md`: Chapter 23 measured `recvmmsg` with 32 datagrams per call only about
5% faster than `recv` with one. Why so little, and when would batching pay more?
