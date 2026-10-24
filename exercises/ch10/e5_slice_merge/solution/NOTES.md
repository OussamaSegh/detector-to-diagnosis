# Exercise 10.5: notes on the solution

**Correctness.** Slices are half-open, [T, T + Δ), so a single on an edge belongs to the
later slice only, and the loop runs until every single has been emitted, so the last partial
slice is never lost. Each slice is gathered board by board, in board order, and sorted with
`std::stable_sort` by `TimeOrder`: equal singles keep board order, which is the heap
merger's tie rule (time, then crystal, then board).

**Measured** (`measurements/ch10/bench_slice_merge.txt`, book VM, GCC 13.3 `-O2`, medians of
5; all singles of 0.1 s at 20 MBq, 10 us slices; the heap merger is given each board's
whole stream at once):

| Boards | Heap merger | Slice and sort |
|---:|---:|---:|
| 4 | 28.0 M singles/s | 48.1 M singles/s |
| 24 | 12.7 M singles/s | 28.4 M singles/s |
| 72 | 10.1 M singles/s | 20.3 M singles/s |

Slice and sort is about twice as fast at every size here. A heap operation per single costs
about log2(boards) comparisons with poorly predictable branches; a sort of a 10 us slice
works on a contiguous array that fits in cache, made of a few long sorted runs.

**What it costs.** Latency and memory. A slice can only be sorted when every board has
passed its end, so data waits up to one slice width plus the boards' skew; the heap merger
releases a single as soon as the watermark passes it. With 10 us slices that is still small
against the pipeline's 500 us batch delay (Chapter 4), so for MiniDAQ the slice design is the
better trade; a design with a hard latency budget would choose Δ from that budget. Both need
the same watermark logic for late and silent boards.
