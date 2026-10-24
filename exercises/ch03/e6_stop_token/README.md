# Exercise 3.6 (M): Shut down a waiting worker promptly

**Goal.** The control thread of a DAQ must be able to stop a stage that is blocked waiting for
work, without a timeout loop and without losing queued items. Implement `ex::Worker`, which
owns a `std::jthread` that waits on a `std::condition_variable_any` with the thread's
`std::stop_token`.

**Time.** 60 minutes.

**Specification.**
- `Worker(handler)` starts the thread. `submit(item)` queues an item and wakes the worker.
- The worker calls `handler(item)` for each item in order.
- `stop()` (and the destructor) request a stop. The worker finishes the items already queued,
  then exits. `stop()` returns once the thread has exited. Items submitted after `stop()` are
  refused (`submit` returns false).
- An idle worker must react to `stop()` within milliseconds: no polling with a timeout.

**Acceptance tests** (`tests/test_worker.cpp`): items are processed in order; queued items
are drained on stop; an idle worker stops in under 100 ms (a watchdog fails the test if it
hangs); TSan clean.

**Hint.** `std::condition_variable_any::wait(lock, stop_token, predicate)` returns when the
predicate is true or a stop was requested. Why does `std::condition_variable` (without
`_any`) not offer this overload?
