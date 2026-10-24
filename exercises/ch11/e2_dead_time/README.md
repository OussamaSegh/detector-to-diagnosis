# Exercise 11.2 (M): Dead time and pile-up in a block detector

**Goal.** Add a dead-time model to the simulator's output: one dead time per block,
non-paralyzable or paralyzable, with optional pile-up, and check the recorded rate against
the two analytical models. This is the plan's "add a dead-time model to the simulator and
check the measured vs true rate curve".

**Time.** 2 hours.

**Starter.** `starter/dead_time.cpp` runs, but has the two models the wrong way round,
loses an event that arrives exactly when the dead time ends, ignores pile-up, and
`recorded_rate` returns the true rate.

**Acceptance** (`tests/test_dead_time.cpp`):
- Hand-made streams: a lost event does not extend a non-paralyzable dead time and does
  extend a paralyzable one; an event exactly tau after the start of the dead time is
  recorded; blocks are independent; pile-up adds the lost energy to the recorded event.
- Poisson arrivals at 5 M/s on one block with tau = 100 ns: the recorded rate is within 1%
  of n / (1 + n tau) and of n exp(-n tau).
- On 3 ms of simulated 30 MBq data with tau = 1 us and pile-up: exactly the singles of
  MiniDAQ's `sim::DeadTime` for both models.

**Then, by hand.** Plot recorded against true rate for both models from 0 to 3 / tau and
mark the maximum of the paralyzable curve. In `NOTES.md`: why does a paralyzable system
have two true rates for each recorded rate, and what does that mean for an operator who
sees the count rate fall when the activity is raised?

**Hints.** Which event starts a non-paralyzable dead time, and which a paralyzable one?
For pile-up you need to find the event a block is recording: keep its index.
