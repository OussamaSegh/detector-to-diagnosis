# Exercise 4.3 (H): Per-stage latency you can query while it runs

**Goal.** The pipeline records a service-time histogram per stage, but only reports it at the
end of a run. An operator (and Chapter 6's control API) needs the *recent* latency while the
acquisition runs: "what was the sort stage's p99.9 over the last second?" Build that, without
adding a lock or a system call to the hot path.

**Time.** 3 hours.

**Tasks.**
1. `ex::StageLatencies(names)` owns one `minidaq::LatencyHistogram` per stage.
   `record(stage, ns)` is called by that stage's thread only (one writer per histogram).
2. `snapshot()` may be called from any thread at any time. It copies every bucket count
   (`LatencyHistogram::count_at`) into a `HistogramSnapshot` per stage.
3. `interval(before, after)` returns, per stage, the number of samples recorded between the
   two snapshots and their p50, p99, p99.9 and maximum (at bucket resolution: report
   `highest_in` of the bucket, as the library does). Do **not** reset the histograms:
   `reset()` races with the writer. Subtract snapshots instead. Throw
   `std::invalid_argument` if the snapshots do not belong to this object or `after` is older
   than `before` (a bucket count went down).
4. `to_json(stats, interval_ns)` renders the result for the control API in the exact format
   shown in the tests, with latencies in microseconds and three decimals, and stage names
   escaped as JSON strings.

**Acceptance tests** (`tests/test_stage_histograms.cpp`): interval percentiles that differ from
the cumulative ones, error cases, exact JSON, and a writer thread recording while a reader
takes snapshots (run it under the `tsan` preset too).

**Hints.** Why is the interval's count the sum of the bucket deltas rather than the difference
of `count()`? Look at the order in which `record()` updates its counters, and at what a reader
running between those stores sees.

**Think about it:** the maximum you report is a bucket bound, not the true maximum. When does
that matter, and how would you track an exact interval maximum with a single writer?
