# Exercise 3.4 (E): Start together, step together

**Goal.** Use `std::latch` and `std::barrier` (C++20) for the two coordination patterns a
DAQ test harness needs most: start all stages at the same moment, and run iterative work
(for example a calibration loop) in lock-step phases.

**Time.** 45 minutes.

**Tasks** (`starter/sync.hpp`):
- `start_together(n)`: start `n` threads; each increments a shared "arrived" counter, waits
  until all `n` have arrived, then records how many had arrived when it started working.
  Return the recorded values. With correct synchronization every value is `n`.
- `phased_sums(values)`: `values[p][w]` is what worker `w` contributes in phase `p`. Each
  worker adds its value to its own partial sum; a `std::barrier` completion function adds the
  partials into the total for phase `p` and resets them, exactly once per phase, before any
  worker starts phase `p + 1`. Return the totals.

**Acceptance tests** (`tests/test_sync.cpp`): every start value equals `n` (repeated 50
times), phase totals are exact, the completion step runs once per phase, and the tests are
clean under TSan.
