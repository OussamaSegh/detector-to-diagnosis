# Exercise 22.4 (H): Fail safe when a supply stops answering

**Goal.** Write the guard that stands between a slow control and a bias supply with a command
interface (a microcontroller or a programmable supply on a serial line): it retries what may be
retried, gives up on time, enters the fail-safe state once and for a reason, and says honestly
whether the supply's output is known to be off.

**Time.** 90 minutes.

**Starter.** `starter/supply_guard.hpp` and `.cpp`: the `Supply` interface (each command can time
out or be refused), the settings, and a guard that does nothing.

**Tasks.**
1. `turn_on(volts, now)`: in state `off`, set the voltage, then switch the output on, each
   command tried at most `max_attempts` times; state `ramping`, with a deadline `settle_ns` after
   `now`. If a command fails every attempt, enter the safe state. Refused (false) in any other
   state.
2. `poll(now)`: in `ramping` and `on`, read the voltage (at most `max_attempts` tries). Within
   `tolerance_v` of the target: `on`. In `ramping` after the deadline, or in `on` outside the
   tolerance: safe state. A read that fails every attempt: safe state.
3. The safe state is entered once: the first reason is kept (`reason()`), and the guard switches
   the output off, with retries. `off_confirmed()` says whether the supply acknowledged it. While
   it has not, every `poll()` tries again to switch the output off, and does nothing else.
4. `acknowledge()`: from the safe state to `off`, only when the output is confirmed off.
5. `clear_trip()` on the supply is not idempotent (it clears the trips that are set when it runs,
   including one that happened since you last read them): the guard never retries it, and calls
   it once when it is acknowledged.

**Acceptance** (`ch22/e4_supply_guard/<variant>/...`): the tests run the guard against a scripted
supply that times out, refuses, answers late, and reports a voltage it does not reach, and count
the commands the guard sends.

Then answer in `NOTES.md`: which of the supply's commands would you retry and which not, and why?
What does the guard do when even the command to switch off fails, and why is that the right thing
to report?
