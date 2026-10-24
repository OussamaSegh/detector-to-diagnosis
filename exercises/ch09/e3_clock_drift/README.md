# Exercise 9.3 (H): Two boards, 20 ppm apart

**Goal.** Two readout boards time stamp with free-running clocks: board A runs 10 ppm
fast, board B 10 ppm slow, with arbitrary offsets. After one second their time stamps
for the same event differ by 20 µs, which is 5,000 coincidence windows of 4 ns. Both boards
also time stamp a sync pulse sent to both at known global times (every millisecond, or
every second). Correct each board's time stamps to global time from its sync stamps, and
estimate the relative drift from the coincidence data alone, without sync pulses.

**Time.** 2.5 hours.

**Starter.** `starter/clock_drift.cpp` has a simulator of the two boards that works, a
correction that removes the offset measured at the first sync pulse and nothing else,
and an estimate that returns 0.

**Acceptance** (`tests/test_clock_drift.cpp`):
- With exact sync stamps, the corrected time difference of every pair is within 5 ps of
  zero, over a full second.
- With 100 ps of jitter per photon and 20 ps per sync stamp, the corrected differences have
  a mean within 5 ps of zero and a standard deviation between 130 and 160 ps (the photons'
  own 141 ps).
- One sync pulse per second is enough for a constant drift: the mean stays within 60 ps,
  set by the jitter of the few sync stamps, where an offset-only correction is microseconds off.
- The drift estimated from the pairs alone is within 0.05 ppm of the true value, and zero
  for two copies of the same clock.

**Hints.** Between two consecutive sync pulses, how does a board's local time relate to
global time? For the estimate: what does tB − tA look like plotted against tA?
