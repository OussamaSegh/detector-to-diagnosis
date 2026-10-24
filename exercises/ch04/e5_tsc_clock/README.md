# Exercise 4.5 (E, extra): A calibrated TSC clock

**Goal.** `clock_gettime(CLOCK_MONOTONIC)` costs tens of nanoseconds on most machines (28 ns on
the book's VM, Section 4.4). Reading the CPU's time-stamp counter (TSC) directly costs a few.
Build a clock that reads the TSC and converts ticks to nanoseconds with a factor calibrated
against `CLOCK_MONOTONIC`, and find out when you may trust it.

**Time.** 60 minutes.

**Tasks.**
1. `ex::read_tsc()`: return the TSC on x86-64 (`__rdtsc()` from `<x86intrin.h>`); return 0 on
   other architectures (the tests then skip).
2. `ex::tsc_is_invariant(cpuinfo_text)`: true when the `flags` line of `/proc/cpuinfo` has
   both `constant_tsc` (fixed rate across frequency changes) and `nonstop_tsc` (keeps
   counting in deep idle states). Match whole words only.
3. `ex::TscClock::calibrate(duration)`: read the TSC and `CLOCK_MONOTONIC` together, sleep for
   `duration`, read both again, and keep the ratio. `now_ns()` returns an estimate of
   `CLOCK_MONOTONIC` in nanoseconds; `ticks_per_us()` returns the measured rate.

**Acceptance tests** (`tests/test_tsc.cpp`, skipped on non-x86-64 machines): the cpuinfo parser on fixed strings; a rate
between 0.5 and 10 GHz; and agreement with `CLOCK_MONOTONIC` within 0.1% over 100 ms after a
50 ms calibration.

**Think about it:** the book's VM reports `constant_tsc` and `nonstop_tsc`, and the kernel
uses the TSC as its clock source. Why do production DAQ systems still timestamp events in the
detector hardware rather than with any PC clock? (Section 4.4.)
