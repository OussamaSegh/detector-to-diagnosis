# Exercise 38.2: notes

The starter fails three tests: a proportional servo settles where its answer cancels the
frequency error (20,000 ppb / 0.7, an offset of about 28.6 us), so neither frequency test ends at
zero, and without a step a 5 ms offset is still there after the first update.

Design choices:

- The integral term is the servo's estimate of the clock's frequency error; once it has learned
  it, the proportional term has nothing left to answer. The closed loop of this discrete servo
  with kp = 0.7 and ki = 0.3 has two poles of magnitude sqrt(0.3), about 0.55, so the offset
  shrinks by about half at every update; it becomes unstable for kp above (4 - ki) / 2, 1.85 with
  these gains. The noise test checks that the gains do not amplify the noise.
- Stepping keeps the integral: a large offset says nothing about the frequency.
- Conditional integration is the simplest anti-wind-up: while the answer is at its limit, the
  integral stays as it was. Without it the integral keeps growing for the 40 s at the limit and
  the clock overshoots by tens of microseconds afterwards.
- Linuxptp's `pi` servo has the same structure, with gains scaled by the update interval and a
  first step that also estimates the frequency from two offsets.
