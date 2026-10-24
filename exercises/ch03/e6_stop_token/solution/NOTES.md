# Exercise 3.6 notes

**The two starter bugs.**
1. The wait predicate only checks the queue, and `std::condition_variable` knows nothing
   about stop tokens, so an idle worker never wakes up when a stop is requested: `stop()`
   hangs in `join()`.
2. The loop condition `while (!st.stop_requested())` exits as soon as a stop is requested,
   abandoning items that are already queued (the test saw 923 of 1,000 processed).

**The fix.** `std::condition_variable_any::wait(lock, stop_token, pred)` registers a stop
callback that notifies the condition variable, then waits until the predicate holds or a stop
is requested. After it returns, an empty queue means "stopped and drained"; anything else is
work to do. Only the `_any` variant has this overload because it works with any lockable and
can carry the extra internal mutex needed to make the stop callback race-free;
`std::condition_variable` is restricted to `std::unique_lock<std::mutex>` so it can be a thin
wrapper over the platform's native condition variable. verify: rationale as given in P0660
(the `std::jthread`/stop-token proposal).

**Lock discipline.** The handler runs without the lock held: user code under a lock invites
deadlock and blocks `submit()` for the handler's duration.

**Member order.** `std::jthread` is the last member, so it is constructed after (and destroyed
before) everything the thread uses.
