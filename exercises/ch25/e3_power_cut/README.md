# Exercise 25.3 (H): Survive a power cut at any step

**Goal.** Install, confirm and roll back versions in two slots so that a power failure after any
single write leaves a system that starts, runs a version that was checked, and can finish the
operation after a restart. The disk is a model (`starter/ab_slots.hpp`), with the four writes
`minidaq_update` makes: extract into a slot, check a slot, write the state, switch `current`. Each
write is atomic; the test cuts the power after every one of them in turn.

**Time.** 90 minutes.

**Starter.** `starter/ab_slots.hpp` (the model; do not change it) and `starter/ab_slots.cpp`.

**Tasks.** `install`, `confirm`, `rollback` and `repair`, as the header's comments say. The
starter's `install` has its writes in an order that loses: start by finding out why.

**Acceptance** (`ch25/e3_power_cut/<variant>/...`): the first installation, an update, a rollback
and a confirmation, each cut after every write; no write when there is nothing to do; and a sequence
of updates that alternates the slots. After every cut, `repair()` must leave the disk in the state
its comment describes, and no write may ever leave `current` on a slot that was not checked.

**Then** answer in `NOTES.md`: `install` records the trial before it switches, and `rollback`
switches before it records. Why are the two orders opposite? And which assumption of the model does
a real file system break if the program forgets to sync the directory after a rename?
