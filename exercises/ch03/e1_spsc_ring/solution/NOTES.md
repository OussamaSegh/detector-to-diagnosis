# Exercise 3.1 notes

**Memory orders.** Each index has exactly one writer. The writer reads its own index with
`relaxed` (no other thread changes it). The producer writes the slot and then stores `tail`
with `release`; the consumer loads `tail` with `acquire` before reading the slot. That
release/acquire pair is what makes the slot contents visible. The same pair on `head` tells
the producer that the consumer has finished reading a slot before it is overwritten.
`seq_cst` would add a full fence on every store on x86 and buys nothing here, because no
decision depends on a single global order of both indices.

**Layout.** `tail` with the producer's cached copy of `head` on one cache line; `head` with
the consumer's cached copy of `tail` on another. Each line is written by one thread only.

**Measured** (4 vCPU Xeon VM at 2.30 GHz, GCC 13.3, -O2, pinned to CPUs 0 and 1, 8 runs of
4 Mi singles each):

| Variant | min | median | max (M singles/s) |
|---|---|---|---|
| per item | 29.2 | 33.3 | 349.6 |
| batches of 64 | 307.2 | 314.4 | 349.7 |
| batches of 256 | 345.6 | 347.8 | 349.4 |

Batching clears the 50 M/s target by a factor of six or more. Per-item transfer did not
reach it on this VM (median 33 M/s for 16-byte singles, against about 52 M/s for 8-byte
words with the library ring) and was very unstable from run to run: one run reached
350 M/s. verify: per-item throughput on bare metal with isolated cores (Chapter 4). The
lesson stands either way: the cost is per hand-off, so hand off batches.
