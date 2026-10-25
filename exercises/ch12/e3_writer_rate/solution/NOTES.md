# Exercise 12.3: notes on the solution

**Design.** Two threads. The caller (the pipeline's writer thread) only encodes into a
block buffer and, when a block closes, moves the buffer to a queue and takes a spare
one. The I/O thread writes queued blocks and calls fsync when the oldest unsynced byte
is `max_unsynced` old, or at the end of the run. Its wait has a deadline
(`wait_until`), so a trickle of data is synced on time even if no block arrives. The
pool of `buffers` blocks bounds the memory (32 x 64 KiB = 2 MiB); when it runs dry the
caller waits, which is backpressure: the pipeline's queues fill and only the source can
drop (Chapter 3). A write error makes the sink faulty; the I/O thread then stops
writing but keeps returning buffers, so the caller never hangs.

**Why the starter was slow.** One fsync per 64 KiB: with a 20 ms fsync, 50 blocks per
second, 200,000 coincidences per second, on the caller's thread. Moving the same work to
another thread is not enough: the I/O thread would then be the bottleneck. One fsync must
cover many blocks: here every block written in the last 100 ms.

**What a power cut can take.** Data in the pool (at most `buffers` blocks), the block
being filled (at most `max_block_delay` in `ListModeSink`; this exercise's sink has no
such limit, so at a trickle a block can wait for its 4,096th record), and data written
but not yet synced (at most `max_unsynced`, 100 ms here). At 5 M coincidences per
second, 100 ms is 500,000 coincidences, 8 MB.

**The measurement** (`measurements/ch12/writer.txt`, the book's VM: 4 vCPU, ext4 on a
virtio disk, 15 GiB RAM, `vm.dirty_ratio` 20%; median of 2 runs of 200 M coincidences,
3.2 GB):

| policy | sustained (M coincidences/s) |
|---|---:|
| none (page cache, no durability) | 29.2 |
| close (one fsync per file) | 19.0 |
| interval, every 256 blocks (16 MiB) | 18.6 |
| interval, every 16 blocks (1 MiB) | 20.5 |

Every policy sustains more than three times the 5 M coincidences per second of the
writer budget of Exercise 11.5 and seven times the 2.7 M the sorter produces at its own
limit (70 M singles per second, 0.039 coincidences per single in `bm_sorter`). On this
disk fsync is cheap enough that syncing every megabyte costs nothing measurable; on a
spinning disk or a network file system it would not be (verify on the acquisition
disk). The choice: `interval` every 256 blocks with a time bound of 100 ms in
production, so that a power cut loses at most a fraction of a second, and `close` for
development. A virtual disk on shared storage is not an acquisition disk: the first dd
of 3 GB ran at 278 MB/s, the second at 1.4 GB/s. (MiniDAQ's `ListModeSink` bounds the
unsynced data by blocks only; a time bound like this exercise's `max_unsynced` is a natural
extension.)
