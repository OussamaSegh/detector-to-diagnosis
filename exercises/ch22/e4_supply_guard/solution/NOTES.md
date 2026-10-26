# Exercise 22.4: notes on the solution

**What may be retried.** A command may be retried when sending it twice has the same effect as
sending it once, and when a failure leaves the device as it was or as the command would have left
it. Setting a voltage, switching the output on or off and reading the voltage all qualify: after a
timeout you do not know whether the supply executed the command, and executing it again does no
harm. Clearing the trip flags does not qualify. It clears whatever is set when it runs; if the
first attempt was executed and only its answer was lost, a second attempt can clear a trip that
happened in between, which nobody has read. The guard sends it once, when an operator acknowledges.

**Bounded, and per call.** Each command is tried at most three times within one call, and the
guard never waits between tries. A guard that retried until success would hold the slow control
on one dead supply while every other board went uncontrolled. Persistence across calls is the
caller's job: the guard is polled every cycle.

**The first reason.** The safe state is entered once, and the reason it keeps is the first. When
a supply stops answering, the reads fail, then the switch-off fails, then the next poll fails
again: each of these is a consequence of the first, and a reason overwritten by the last
consequence sends the investigation to the wrong place.

**When even the switch-off fails.** Then the output may still be on, and the guard says so:
`off_confirmed()` is false, `acknowledge()` refuses, and every poll tries to switch off again,
because that is the only command that still matters. Reporting "safe" without the confirmation
would let an operator re-arm, or walk up to, a detector that is still biased. The honest state is
"safe requested, not confirmed", and what protects the detector then is the hardware's own
protection and a person who goes to look.
