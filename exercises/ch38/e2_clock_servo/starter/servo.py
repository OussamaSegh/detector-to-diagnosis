# SPDX-License-Identifier: MIT
"""Exercise 38.2: the servo that keeps a clock on time (starter)."""
from dataclasses import dataclass


@dataclass
class Correction:
    step_ns: float = 0.0  # subtract this from the clock now
    freq_ppb: float = 0.0  # and slow it down by this much (ns per s) until the next update


class Servo:
    def __init__(self, kp=0.7, ki=0.3, step_ns=100_000.0, max_ppb=500_000.0):
        self.kp, self.ki, self.step_ns, self.max_ppb = kp, ki, step_ns, max_ppb

    def update(self, offset_ns, dt_s=1.0):
        """The correction for a measured offset (clock minus reference) every dt_s seconds."""
        return Correction(0.0, self.kp * offset_ns / dt_s)
