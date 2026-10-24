# Exercise 4.6 (M, extra): Coordinated omission

**Goal.** A load tester that sends the next request only after the previous one completed
"coordinates" with the system it measures: during a stall it stops sending, so it records one
slow sample where an open stream of requests (or of detector data, which does not wait)
would have seen hundreds. Reproduce the effect in a deterministic simulation and fix it the
two standard ways.

**Time.** 90 minutes.

**Tasks.**
1. `ex::simulate_closed_loop(n, interval_ns, service_ns)` models a tester that intends to start
   request `i` at `i * interval_ns`, but starts it only when request `i - 1` has finished:
   `start[i] = max(i * interval_ns, end[i - 1])`, `end[i] = start[i] + service_ns(i)`. Return
   the intended starts, actual starts and ends.
2. `ex::record_naive(h, run)`: record `end - start` for every request (what the tester reports).
3. `ex::record_from_intended(h, run)`: record `end - intended` (what a client that arrived on
   schedule would have experienced).
4. `ex::record_corrected(h, value, expected_interval)`: the HdrHistogram-style correction
   applied to a single naive measurement: record `value`, then, while it is larger than the
   expected interval, also record `value - interval`, `value - 2 * interval`, and so on, down
   to (but not including) values at or below the interval. This is what you do when you only
   have the naive numbers but know the intended rate.

**Acceptance tests** (`tests/test_omission.cpp`): 10,000 requests every 1 ms, each served in
100 us, except one that stalls for 200 ms. The naive p99 stays at 100 us; the two corrected
measurements both put the p99 above 90 ms (a factor of about 1,000), and agree with each other
within 15%.

**Think about it:** the MiniDAQ source records `Batch::origin_ns` when the first word of a
batch *arrives*, not when it was taken out of the hardware FIFO. Does `minidaq_latency`
suffer from coordinated omission? What about Chapter 3's `PacedSource` when the pipeline
applies back-pressure?
