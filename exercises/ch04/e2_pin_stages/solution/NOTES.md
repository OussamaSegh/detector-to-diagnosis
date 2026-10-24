# Exercise 4.2 notes

**cpulist.** The format is small but the error cases matter: a profile generated from a
mistyped `isolcpus=` that silently becomes "no isolated CPUs" puts your FIFO threads on the
CPU that handles interrupts. Rejecting everything that is not exactly `N` or `A-B` (no
spaces inside, no hex, no empty items) is deliberately strict.

**Placement.** The rule "busy stages first, one per CPU, everything else on housekeeping"
keeps the invariant that matters: a `SCHED_FIFO` stage that polls never shares a CPU with
another runnable thread of equal or lower priority it would starve. Pair and write do little
work per batch in this pipeline, so they can live with the operating system; they block on
their input channels and use the normal scheduler.

**Measurements** (book machine, 4 vCPU VM, `minidaq_latency --rate 10e6 --seconds 20
--batch 4096`, three runs each, median; load is `stress-ng --cpu 4 --vm 2 --vm-bytes 256M --io 1`;
end-to-end latency in milliseconds, measured from when the data was due):

| Condition | Profile | Dropped | Behind at stop | p50   | p99   | p99.9 |
|-----------|---------|---------|----------------|-------|-------|-------|
| idle      | default | 0       | 0              | 0.78  | 1.8   | 5.8   |
| idle      | rt-pin  | 0       | 0              | 0.75  | 2.2   | 5.8   |
| idle      | rt-fifo | 0       | 0              | 0.70  | 44.0  | 50.1  |
| load      | default | 11.6%   | 24%            | 2,835 | 4,765 | 4,918 |
| load      | rt-pin  | 4.9%    | 37%            | 3,221 | 7,315 | 7,416 |
| load      | rt-fifo | 0       | 0              | 5.6   | 51.6  | 61.1  |

Idle, pinning changes little and `SCHED_FIFO` hurts: the source is busy about 90% of the time,
hits the real-time throttle, and stalls for tens of milliseconds every second. Under load, a
pinned `SCHED_OTHER` source is *worse* than an unpinned one, because it cannot escape the load on
its CPU; `SCHED_FIFO` on the pinned busy stages is the only profile that keeps up. On the
acquisition PC you would isolate the busy CPUs instead of fighting for them (verify there).

**Splitting a stage.** Sort is the bottleneck at large batches (Chapter 3); with more cores,
partition it by detector sector (each partition sorts its own crystals, then a k-way merge),
which adds one dedicated CPU per partition plus one for the merge.
