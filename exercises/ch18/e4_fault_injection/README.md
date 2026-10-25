# Exercise 18.4 (M): A detector that fails on purpose

**Goal.** Write `FaultInjectingDetector`, a `DetectorPort` that wraps another port and injects
the failures a test needs: a fault after a given number of words, a dropped word every n-th
word, and a stall of a few reads. Then use it to show that the acquisition service ends a run
in a fault, and that a dropped word makes the run incomplete.

**Time.** 90 minutes.

**Starter.** `starter/fault_injection.hpp` declares the class and the `FaultPlan`;
`starter/fault_injection.cpp` passes every word through and injects nothing.

**Acceptance** (`tests/test_fault_injection.cpp`, run as `ch18/e4_fault_injection/<variant>/...`):
- Without a plan the decorator is transparent; it describes itself as
  `fault-injecting(<inner>)`.
- With `fault_after_words = N` it delivers exactly N words whatever the read sizes, then reports
  the plan's message as its fault, delivers nothing more and does not read the inner port again.
  A fault of the inner port is always reported.
- With `drop_every = n` it drops words n, 2n, 3n, ... of the inner stream, across reads, and
  reports them in a counter after the inner port's counters, which it passes on unchanged.
- A stall returns 0 without reading the inner port; the stream continues afterwards.
- In front of the service's simulated detector: the run ends in the `fault` state with
  `detector: <message>`, and a run with dropped words is not `complete`.

Then answer in `NOTES.md`: when is a decorator like this a better test double than a fake that
generates everything itself, and when is a mock (GoogleMock) better than both?

**Hints.** `read()` runs on the source thread; `fault()` and `counters()` on the service's
monitor thread. How does the run's integrity verdict decide which detector counters are losses?
Read `assess_integrity` in `minidaq/src/control/run_integrity.cpp` before you name the counter.
