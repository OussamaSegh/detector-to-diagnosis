# Exercise 22.2 (M): A bias controller with limits and alarms

**Goal.** Write the decision of one slow-control cycle for one board: the SiPM bias for the
measured temperature, inside limits, written only when it moved enough; a temperature warning with
hysteresis; an alarm that switches the bias off and stays latched until an operator acknowledges
it; and a temperature reading that is not believed.

**Time.** 60 minutes.

**Starter.** `starter/bias_controller.hpp` and `.cpp`: the settings, the decision a cycle returns
and the class, with a `step()` that decides nothing.

**Tasks.** `step(temperature_c)` returns a `Decision`:
1. The target bias is `vbd_25c_mv + k_mv_per_c * (T - 25) + vov_mv`, clamped to `min_mv` and
   `max_mv`; `at_limit` says whether the clamp changed it.
2. `write_mv` holds the clamped bias, rounded to a whole millivolt, on the first step and on the
   first step after an acknowledgment, and afterwards only when it differs from the last value
   written by at least `step_mv`; otherwise it is empty.
3. The level is `warning` from `warning_c` on, and goes back to `normal` only below
   `warning_c - hysteresis_c`.
4. At `alarm_c` or above the controller latches: `bias_on` is false and the level `alarm`. A
   temperature that is NaN or below `min_c` latches too, with the level `invalid`. While latched,
   every step returns `bias_on == false`, nothing to write, and the level of the latch, whatever
   the temperature.
5. `acknowledge()` clears the latch; the next step decides from its temperature, as on the first
   step.

**Acceptance** (`ch22/e2_bias_control/<variant>/...`): the tests of the law, the limits, the
update step, the hysteresis, the latch and its acknowledgment, and the readings not believed.

Then answer in `NOTES.md`: why does the alarm latch and the warning not? What goes wrong with a
warning that latches, and with an alarm that clears itself?
