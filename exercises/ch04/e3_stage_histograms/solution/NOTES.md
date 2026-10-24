# Exercise 4.3 notes

**Why subtract instead of reset.** `LatencyHistogram::record()` is a single-writer
load-plus-store. If a reader calls `reset()` between the writer's load and its store, the
writer stores the old count plus one and the reset is undone for that bucket: a lost update,
and a data race under the C++ memory model's definition only if the accesses were not atomic
(they are, so it is "just" wrong, not undefined). Subtracting two snapshots needs no
cooperation from the writer at all. HdrHistogram's `Recorder` solves the same problem with a
phase flip between two histograms, which also gives an exact interval min and max; it costs
an extra atomic on every record (verify: see the HdrHistogram Java `WriterReaderPhaser`
documentation).

**Count from buckets.** `record()` bumps the bucket, then the total. A snapshot taken
between the two stores has one more sample in its buckets than in `count()`. Computing the
interval count from bucket deltas keeps every percentile consistent with the count it was
computed from, and the concurrent test shows every sample lands in exactly one interval.

**Snapshot cost.** About 4,000 buckets per stage (about 34 KiB): copying five of them once a
second is negligible, but do not snapshot from the hot path.

**Exact interval maximum.** The bucket bound is within 0.8% of the true value, which is
enough for an operator display. For an exact maximum, give the writer a second atomic it
resets itself when the reader asks (the reader sets a flag; the writer exchanges its running
maximum when it sees the flag): the writer stays the only thread that writes the value.

**Wiring.** Chapter 6 exposes `to_json()` through the control API's `stats` command; the pipeline
already records per-stage service time, so the change there is to keep one snapshot per
client and answer with the interval since its last request.
