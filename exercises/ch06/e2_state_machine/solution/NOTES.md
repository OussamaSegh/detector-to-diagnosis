# Exercise 6.2: notes on the reference solution

- **One table.** The 15 legal transitions are a `constexpr` array searched linearly. With 42
  pairs, a search is as fast as anything cleverer and much easier to review than a nested
  `switch`, and the same table can be exported for diagrams and documents.
- **Illegal is not exceptional.** `apply` returns `Expected<State, Illegal>`: a refused
  command is a normal outcome that the control API reports to the operator, not a bug.
- **Listener order without holding the lock.** Calling the listener under the state mutex
  gives order for free, but a listener that calls `state()` then deadlocks on a
  non-recursive mutex, and anything slow in a listener blocks every `state()` caller (the
  control API's `status`). The solution takes a *ticket* (a sequence number) while holding
  the state lock, releases it, and then waits on a second mutex and condition variable until
  all earlier tickets have been served. The listener runs under the second mutex only, so
  calls never overlap and come in ticket order. The state mutex is never held while the
  second one is taken, so there is no lock-order inversion. ThreadSanitizer flagged the
  first version of MiniDAQ's machine, which held both: that is why the test reads the state
  from inside the listener.
- **What the listener sees.** The listener receives the transition it is told about; when it
  calls `state()` it may already see a later state if another thread moved on. That is why
  the transition, not `state()`, is passed to it.
- **Testing concurrency.** The concurrent test cannot predict the history, so it checks an
  invariant instead: the history is a chain (each `from` equals the previous `to`), every
  link is legal, and its length equals the number of successful `apply` calls.
