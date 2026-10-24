# Exercise 3.2 (M): Catch a seeded race with ThreadSanitizer

**Goal.** `ex::EnergyMonitor` is shared by two decoder threads, which record energies into a
histogram, and a control thread, which publishes a new energy window that the decoders read.
The starter contains two data races of different kinds. Find both with ThreadSanitizer (TSan),
fix them, and write a short report.

**Time.** 90 minutes.

**Steps.**
1. Build the starter under TSan and run its tests:

       cmake --preset tsan -DMINIDAQ_BUILD_STARTERS=ON
       cmake --build --preset tsan --target ch03_e2_seeded_race_starter
       ctest --preset tsan -L starter -R ch03/e2

2. Read each report: the two conflicting accesses, their stacks, and the thread creation
   points. Note which race the ordinary (non-TSan) test run also catches and which it does not.
3. Fix the code with the weakest synchronization that is correct, and say why it is enough.
4. Write `REPORT.md` next to your code: for each race, the TSan excerpt, the root cause, the
   fix, and how you know it is fixed.

**Acceptance tests** (`tests/test_monitor.cpp`):
- Two threads record 500,000 energies each: the total and the sum of the bins are exactly
  1,000,000.
- A window published by one thread is seen by another thread either completely old or
  completely new, never mixed, and with no TSan report.
- The whole test binary runs clean under the `tsan` preset (the preset sets
  `halt_on_error=1`, so any report fails the test).
