# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 38.2: a simulated clock disciplined by the servo."""
import random
import statistics
import unittest

from servo import Servo


def run(servo, steps, error_ppb, offset_ns=0.0, noise_ns=0.0, seed=38):
    """The true offsets after each update of a clock that runs fast by error_ppb(k) ns per s,
    measured once per second with Gaussian noise; the servo's answer holds until the next one."""
    rng = random.Random(seed)
    out = []
    for k in range(steps):
        c = servo.update(offset_ns + rng.gauss(0.0, noise_ns), 1.0)
        offset_ns -= c.step_ns
        offset_ns += (error_ppb(k) - c.freq_ppb) * 1.0
        out.append(offset_ns)
    return out


class Servo_(unittest.TestCase):
    def test_a_constant_frequency_error_ends_at_offset_zero(self):
        # A crystal 20 ppm fast: 20,000 ns per second.
        offsets = run(Servo(), 80, lambda k: 20_000.0)
        self.assertLess(max(abs(o) for o in offsets[-10:]), 1.0)

    def test_a_change_of_frequency_is_learned_again(self):
        # The room warms up: the error goes from 20 to 23 ppm at the 60th second.
        offsets = run(Servo(), 160, lambda k: 20_000.0 if k < 60 else 23_000.0)
        self.assertGreater(max(abs(o) for o in offsets[60:70]), 100.0, "the change is seen")
        self.assertLess(max(abs(o) for o in offsets[-10:]), 1.0)

    def test_a_large_offset_is_stepped_not_slewed(self):
        # The clock starts 5 ms off: slewing at the limit of 500 ppm would take 10 s, and the
        # first answer must already have put it within the step threshold.
        offsets = run(Servo(), 40, lambda k: 0.0, offset_ns=5_000_000.0)
        self.assertLess(abs(offsets[0]), 100_000.0)
        self.assertLess(max(abs(o) for o in offsets[-5:]), 1.0)

    def test_the_limit_does_not_wind_up_the_integral(self):
        # 80 us off, below the step threshold, with a small limit of 2,000 ppb: 40 s at the limit.
        # Once there, the clock must not overshoot by more than a tenth of where it started.
        servo = Servo(max_ppb=2_000.0)
        offsets = run(servo, 200, lambda k: 0.0, offset_ns=80_000.0)
        self.assertGreater(min(offsets), -8_000.0)
        self.assertLess(max(abs(o) for o in offsets[-10:]), 1.0)

    def test_noise_is_not_amplified(self):
        # Time stamps with 50 ns of noise: the clock stays within about that.
        offsets = run(Servo(), 400, lambda k: 20_000.0, noise_ns=50.0)
        self.assertLess(statistics.pstdev(offsets[100:]), 80.0)


if __name__ == "__main__":
    unittest.main()
