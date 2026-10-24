# Exercise 3.4 notes

- `std::latch` is single-use: perfect for "start together". `arrive_and_wait()` both counts
  this thread in and blocks until the count reaches zero.
- `std::barrier` is reusable and runs its completion function once per phase, on one of the
  participating threads, after all have arrived and before any is released. That is why the
  completion function can read and reset the per-worker partials without atomics: the barrier
  orders every worker's writes before it and its writes before the next phase.
- The completion function must not throw (the standard requires it to be callable as
  `noexcept`); ours is marked `noexcept`.
- Partials are in a `std::vector<std::int64_t>` and adjacent workers share cache lines. For four
  workers and one write per phase that does not matter; for hot per-worker counters use
  `minidaq::CacheAligned` (Chapter 2).
