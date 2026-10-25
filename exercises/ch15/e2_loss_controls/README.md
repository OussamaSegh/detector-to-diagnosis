# Exercise 15.2 (M): Risk controls for silent event loss

**Goal.** Implement two software risk controls for the hazard "coincidence data lost without
notice": the acquisition invalidation, which judges a run complete or incomplete from every
loss counter and the fault, and a loss alarm that an operator sees during the run. Then trace
both to their tests.

**Time.** 2 hours.

**Starter.** `starter/loss_controls.cpp`: `assess()` looks only at lost packets and ignores
the fault; `LossAlarm::update()` compares the run's totals, so it neither sees a burst late in
a long run nor stays raised.

**Acceptance** (`tests/test_loss_controls.cpp`, run by CTest as
`ch15/e2_loss_controls/<variant>/...`):
- `assess()` invalidates a run for every nonzero loss counter and for a fault, and lists the
  nonzero counters in the order of `Counters`.
- `LossAlarm` is raised when the loss between two updates exceeds the fraction of packets sent
  in that interval (lost plus received), stays raised until acknowledged, starts afresh when
  the counters go backward, raises on any loss at a fraction of 0, and rejects a fraction
  outside [0, 1).

Then write in `NOTES.md` a table with one row per control: the control, its type (inherent,
protective, information), the requirement you would write for it, and the tests that verify
its implementation and its effectiveness. Which of the two is MiniDAQ's RC-01?

**Hints.** MiniDAQ's own invalidation is `minidaq/src/control/run_integrity.cpp`. The alarm's
interval is the service's monitor period; think about what "since the last update" means
when the run ends and the next one starts.
