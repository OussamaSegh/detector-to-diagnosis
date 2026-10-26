# Exercise 25.3: notes on the solution

**One invariant, checked after every write.** The system must be able to start whenever the power
fails, so `current` must always name a slot whose files were checked. That rules out extracting into
the slot that runs and switching to a slot before it is checked. It leaves extract, check, then
record and switch; the only question is the order of the last two.

**Record, then switch (install).** A cut between them leaves a state with a trial that is not
current. `repair()` reads that as "the trial never ran" and forgets it; the good version runs and
the update can be installed again. Switch first, and a cut leaves the new version running while the
state still says the old one is the only version: the trial would be running without being known as
a trial, and the next update would overwrite the old good version, the way back.

**Switch, then record (rollback).** Here the safe direction is the opposite. Switch first, and a cut
leaves the good version running with a trial still recorded but not current, which `repair()`
discards: the rollback is complete. Record first, and a cut leaves the trial running with no trial
in the state: the untested version would look confirmed. In both operations the rule is the same: at
every moment, the state on disk may only claim something that is safer than the truth.

**repair() is the other half of the design.** Each order works only because `repair()` knows how
each operation can be cut and what the remains mean. The same three rules are in `SlotStore::open`
(`minidaq/src/update/slots.cpp`), and the unit test
`Update.APowerCutAfterAnyStepLeavesAVersionThatRuns` cuts the real updater in the same way, with a
hook after each step.

**What the model assumes.** It assumes each write is atomic and durable in the order it was made. On
Linux, a rename is atomic, but it is durable only once the directory that holds it is synced
(`fsync` on the directory), and a file's contents only once the file is synced. Without those syncs,
a power cut can leave the rename of `current` on disk and the extracted files not, or the reverse.
The real updater flushes the slot's file system with `syncfs` once the slot is checked, writes the
state to a temporary file that it syncs and renames, and syncs the root directory after each rename
(`write_atomically`, `sync_path`), which is what makes the model's assumption true. A model that is
easier than reality is only useful when the code makes reality match it.
