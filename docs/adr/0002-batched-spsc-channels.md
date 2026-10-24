# 0002. Batched SPSC channels between pipeline stages

Date: 2026-10-24
Status: Accepted

## Context

The pipeline (source, decode, sort, pair, write) runs one thread per stage and must sustain
at least 10 M singles/s with headroom for 30 M/s (docs/performance-budget.md) without
allocating, locking or making system calls per event. Order matters: batch 1001 must be
paired after batch 1000. Losing data inside the PC is never acceptable; only the source may
drop, and only by policy and with a count (Chapter 3, Chapter 15).

Measured in Chapter 3 on the book's machine (4 vCPU Xeon VM, GCC 13.3, -O2,
`bm_spsc --benchmark_repetitions=10`, median millions of items per second):

| Hand-off | Median M items/s |
|---|---|
| `std::mutex` + `std::deque` | 5.2 |
| `minidaq::MpmcQueue`, one producer and one consumer | 28.7 |
| `minidaq::SpscRing`, one item at a time | 51.6 |
| `SpscRing`, batches of 256 | 386.8 |

## Options

1. **A mutex-protected queue per stage boundary.** Simple and obviously correct, but 5 M
   items/s is below the requirement, and a lock on the hot path brings priority inversion
   (Chapter 4).
2. **A bounded MPMC queue** (`MpmcQueue`), which would also allow several workers per stage.
   Faster than the mutex, but pays for multi-producer safety that one producer does not need,
   and several consumers would break ordering.
3. **SPSC rings carrying pointers to pre-allocated batches**, with a second ring returning
   empty batches (`minidaq::Channel`).
4. **One thread doing everything** (no hand-off at all). Fastest per event while it keeps up,
   but no stage can be isolated, pinned or measured separately, and one slow step stalls all.

## Decision

Option 3. Each stage boundary is a `Channel<T>`: a fixed pool of `Batch<T>` objects that
circulate between two SPSC rings, full batches downstream and empty ones back. Batch size
and pool depth are configuration (`pipeline.batch_size`, `pipeline.batches_per_channel`;
defaults 4,096 and 64). Back-pressure appears in exactly one place: a producer that finds no
empty batch. Where a stage later needs several producers (several readout links, Chapter 9),
an MPMC or MPSC queue of batches is used at that boundary only.

## Consequences

### Positive

- The hand-off costs one index update per batch, not per event: the measured gap to the
  mutex queue is about 70x.
- No allocation after start: every batch exists before the first word arrives.
- Ordering is preserved by construction, and every stage is a thread that can be pinned
  and measured on its own (Chapter 4).

### Negative

- Latency has a floor of up to one batch: at 1 M singles/s, a 4,096-single batch takes 4 ms
  to fill, so `pipeline.max_batch_delay_us` (default 500) sends partial batches.
- Memory is reserved for the worst case: 4 channels x 64 batches x 4,096 items.
- A stage cannot be parallelized by adding consumers; that needs an explicit split and merge
  (Chapter 10).
