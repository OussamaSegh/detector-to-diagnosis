# SPDX-License-Identifier: MIT
"""Exercise 38.2: the servo that keeps a clock on time (solution)."""
from dataclasses import dataclass


@dataclass
class Correction:
    step_ns: float = 0.0  # subtract this from the clock now
    freq_ppb: float = 0.0  # and slow it down by this much (ns per s) until the next update


class Servo:
    """A proportional-integral servo, as PTP clients use (linuxptp's "pi" servo works this way).

    The proportional term answers the offset now; the integral term learns the clock's frequency
    error, so that a clock that runs fast by a constant amount ends at offset zero instead of at
    the offset whose proportional answer cancels the error. An offset above step_ns is stepped at
    once rather than slewed, which at max_ppb would take hours. While the answer is limited to
    max_ppb, the integral does not grow (no wind-up), or it would overshoot for as long afterwards.
    """

    def __init__(self, kp=0.7, ki=0.3, step_ns=100_000.0, max_ppb=500_000.0):
        self.kp, self.ki, self.step_ns, self.max_ppb = kp, ki, step_ns, max_ppb
        self.integral = 0.0  # ns per s: the frequency error learned so far

    def update(self, offset_ns, dt_s=1.0):
        """The correction for a measured offset (clock minus reference) every dt_s seconds."""
        if abs(offset_ns) > self.step_ns:
            return Correction(offset_ns, self.integral)
        integral = self.integral + self.ki * offset_ns / dt_s
        freq = self.kp * offset_ns / dt_s + integral
        if abs(freq) > self.max_ppb:
            return Correction(0.0, max(-self.max_ppb, min(self.max_ppb, freq)))
        self.integral = integral
        return Correction(0.0, freq)
