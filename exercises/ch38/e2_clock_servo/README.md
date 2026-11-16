# Exercise 38.2 (M): The servo that keeps a clock on time

**Goal.** Write the proportional-integral servo with which a PTP client steers its clock: from
each measured offset, a frequency correction that brings the offset to zero and keeps it there,
a step for an offset too large to slew, and a limit that does not wind up.

**Time.** 2 hours.

**What to write** (`servo.py`): `Servo.update(offset_ns, dt_s)` returns a `Correction` with
`step_ns` (subtract this from the clock now) and `freq_ppb` (run this many nanoseconds per second
slower until the next update).
- An offset larger than `step_ns` is stepped at once.
- Otherwise the answer is `kp * offset / dt` plus an integral term that learns the clock's
  frequency error (`ki * offset / dt` added at every update).
- The answer is limited to `max_ppb`; while it is, the integral term does not change.

**Starter.** `starter/servo.py` is proportional only and never steps.

**Acceptance** (`tests/test_servo.py`, a simulated clock measured once per second):
- A clock 20 ppm fast ends within 1 ns of the reference after 80 s; when its error changes to
  23 ppm, the servo learns it again.
- A clock 5 ms off is within the step threshold after the first update.
- Starting 80 us off with a limit of 2,000 ppb, the clock does not overshoot by more than 8 us.
- With 50 ns of measurement noise, the clock's offset varies by less than 80 ns rms.

**Then, by hand.**
1. With the proportional term alone, where does a clock 20 ppm fast settle, and why?
2. Raise `kp` to 1.5 and to 2.5. What happens, and why does the loop become unstable a little
   below 2?
3. What does a smaller `ki` buy and cost when the measurements are noisy?
