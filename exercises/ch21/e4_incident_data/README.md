# Exercise 21.4 (M): What went wrong first

**Goal.** Reconstruct an incident from monitoring data: given the status snapshots a script
polled about once a second, find which pipeline stage slowed first and when, and when the source
began to lose data. In a pipeline with bounded queues a slow stage soon slows every stage before
it, so "the one that is slow now" is often the wrong answer; the order of the onsets is the
evidence.

**Time.** 60 minutes.

**Starter.** `starter/incident.py`, four functions to write. `tests/pipeline_sim.py` makes the
snapshots of incidents with a known cause: a one-second model of MiniDAQ's five stages in which
one stage's capacity falls to 30% at a given second.

**Tasks.**
1. `rates(snapshots, stage)`: items per second between consecutive snapshots, divided by the real
   time between them. Leave out an interval in which the counter went down (a restart).
2. `onset(snapshots, stage)`: the first time the rate is below half the stage's median rate of
   the first ten seconds.
3. `first_to_slow(snapshots)`: the stage with the earliest onset; if several slowed in the same
   interval, the one furthest downstream.
4. `loss_began(snapshots)`: the first snapshot whose `dropped` count went up.

**Acceptance** (`ch21/e4_incident_data/<variant>/unittest`): a steady run has the offered rate
and no onset; a restart and a missed snapshot are handled; the slow stage is found whichever of
the five it is; the stages before it slow later, in order; loss begins only when the queues are
full, well after the slowdown.

Then answer in `NOTES.md`: the operator's report says "the writer stopped keeping up at 14:32".
What do you ask for before you agree, and what would the flight recorder have added?
