# Exercise 4.6 notes

**Numbers.** In the simulation, 1 request in 10,000 stalls for 200 ms. The naive tester
reports p99 = p99.99 = 100 us: the stall shows up only in the maximum. Measured from the
intended start, 223 requests are late (the tester catches up 0.9 ms per fast request), and p99
is 110 ms. The HdrHistogram-style correction adds 198 synthetic samples (199 ms down to 2 ms)
and gives p99 = 99 ms. The two corrections differ because the correction assumes the missing
requests would each have waited for the stall to end and nothing more, while the intended-start
measurement also charges the queue that builds up behind it.

**Which to use.** If you control the load generator, measure from the intended start (that is
what tools such as `wrk2` do, verify: see its README). Use `record_corrected` only on
measurements you cannot redo, and say so in the report.

**MiniDAQ.** It did, until this chapter. The source stage set `Batch::origin_ns` when it
*read* the first word of a batch, so when the source thread itself was delayed (throttled,
preempted, or slower than the input), its backlog was read late, stamped late, and the stall
vanished from the histogram. Under load, the read-time measurement reported a median of 20 ms;
measured from when the data was due, the median was nearly 3 seconds, because the source never
caught up. The fix is `PipelineConfig::due_time_ns`: `minidaq_latency` passes
`PacedSource::due_ns`, and a real receiver would pass the hardware timestamp. `minidaq_latency`
also prints the backlog (`behind schedule`) and the drops next to the percentiles: words that
were dropped or never read have no latency at all, so a run with either is not a valid latency
result. With the block policy the same thing happens through back-pressure: the source waits,
reads late, and under-reports unless the due time is used.
