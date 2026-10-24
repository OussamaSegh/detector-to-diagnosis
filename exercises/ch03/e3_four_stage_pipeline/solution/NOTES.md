# Exercise 3.3 notes

**Structure.** Three `minidaq::Channel`s; every batch is allocated before the threads
start. Threads are created consumers first. Each stage closes its output when its input is
closed and drained; the consumer checks `receive()` once more after it sees `closed()`, so a
batch published just before `close()` is never lost.

**Reports.** Each `StageReport` is written by one thread only and read after the threads are
joined (joining is a synchronization point), so plain integers are fine. A live monitor that
reads them while the pipeline runs needs atomics, as in `minidaq::StageStats`.

**Busy time** brackets only the processing of a batch, not the waits, so `in / busy_seconds`
is the throughput the stage could sustain if it never waited. The stage with the lowest value
limits the pipeline.

**What to expect** (from the library pipeline on the book's VM, 8 Mi words):
the sort stage is the bottleneck. Sorting each batch costs O(n log n), so its per-single cost
grows with the batch size: about 90, 45 and 36 M singles/s for batches of 64, 512 and 4096.
At 64 the per-batch hand-off overhead dominates instead. 512 was the best compromise. Chapter
10 replaces the per-batch sort with a merge that exploits the near-sorted input.
