# Exercise 6.2 (M): Implement the state machine, with a calibration state

**Goal.** Implement an acquisition state machine from a written specification, so that every
illegal command is harmless, every transition is reported exactly once and in order, and
the machine stays consistent when several threads send events at once. The specification
extends MiniDAQ's machine with one state, so you cannot copy the table: you must read it.

**Time.** 2 hours.

**Specification.** States: idle, configured, calibrating, running, stopping, fault. Events:
configure, calibrate, start, stop, drained, error, reset. The legal transitions are exactly:

| From | Event | To |
|---|---|---|
| idle | configure | configured |
| configured | configure | configured |
| configured | calibrate | calibrating |
| calibrating | drained | configured |
| configured | start | running |
| configured | reset | idle |
| running | stop | stopping |
| running | drained | configured |
| stopping | drained | configured |
| any state except fault | error | fault |
| fault | reset | idle |

**Tasks.**
1. Before you write any code, write down on paper which of the 42 state/event pairs are
   legal. Then implement `next_state` with one `constexpr` table in `state_machine.cpp`.
2. Implement `to_string`, `Illegal::message()` ("cannot start in state idle") and
   `Machine::apply`: legal events change the state and return it; illegal ones return
   `Illegal` and change nothing.
3. Call the listener once per transition, in the order the transitions happened, never two
   at a time, and *without* holding the lock that `state()` takes: a listener may call
   `state()`.

**Acceptance tests** (`tests/test_state_machine.cpp`): all 42 pairs against an independent
copy of the specification; illegal events leave the state unchanged with the exact message;
listener order; a listener that reads the state (a watchdog fails the test on deadlock);
4 threads sending 80,000 random events, after which the listener's history must be one
consistent chain of legal transitions. Run it under the `tsan` preset too.

**Hints.** The easy way to keep the listener in order is to call it while holding the state
lock. What happens when the listener calls `state()`? And if you use a recursive mutex
instead, what happens when the listener does something slow? MiniDAQ's own
`StateMachine::apply` shows one answer (tickets); find your own before you read it.
