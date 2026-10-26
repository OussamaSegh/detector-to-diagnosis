# Exercise 22.2: notes on the solution

**Why the alarm latches.** An alarm switches the bias off. If it cleared itself, a detector that
overheats every few minutes would have its bias switched off and on during a scan, and the run's
data would be a mixture of periods at the calibrated gain, periods without data and periods during
the ramp, with nobody having decided to keep any of it. A latched alarm turns that into one event
that a person sees and decides on: wait, fix the cooling, or end the scan. The acknowledgment is
that decision, and if the cause is still there the alarm latches again at once.

**Why the warning does not.** A warning changes nothing in the hardware; it tells an operator that
the detector is running warm. A latched warning would stay on the screen after the temperature
has gone back to normal, and an operator who sees a warning that is no longer true learns to
ignore warnings. The hysteresis does the other half of the job: without it a temperature hovering
at 35.0 °C would raise and clear the warning every cycle.

**NaN.** Every comparison with NaN is false, so `t < min_c` and `t >= alarm_c` both let a NaN
through, and the law then computes a NaN bias, which `std::clamp` returns unchanged. A temperature
from a failed conversion, a division by a zero calibration or an uninitialized value must be
refused by name.

**Rounding before comparing.** The step is compared between whole millivolts, the values actually
written, so that the setpoint moves in steps of at least 5 mV of what the supply receives, not of
what the arithmetic produced.
