# Exercise 6.5: notes on the reference solution

- **A decorator.** `FaultyDetector` is itself a `DetectorPort` that owns another one. The
  service cannot tell the difference, which is the point of the port: the same fault
  handling runs in tests and in production.
- **Threads.** `read()` runs on the source thread; `fault()` on the service's monitor
  thread. Only the link-down flag is shared, so it is an atomic; the counters the test reads
  afterwards are atomics in a `shared_ptr`, because the service destroys the detector when
  the run is reset.
- **Stall and latency.** The inner `SimulatedDetector` paces by wall-clock time, so during a
  stall its words keep coming due. After the stall they are delivered at once, with due
  times 60 ms in the past, and the end-to-end maximum shows it. Nothing is lost because the
  pipeline applies back-pressure (overflow "block"). With overflow "drop" and a long enough
  stall, you would see the source's dropped counter rise instead.
- **Reordering.** Holding back words for longer than a batch guarantees that they arrive in a
  later batch than newer words. A shorter delay could be repaired by the per-batch sort and
  would not be detected, which is a property worth knowing about the Chapter 3 sorter, and
  one the Chapter 10 sorter must handle deliberately.
- **Due times while reordering** are approximate in this adapter (the indices shift while
  words are held back); the test that uses reordering does not look at latency.
