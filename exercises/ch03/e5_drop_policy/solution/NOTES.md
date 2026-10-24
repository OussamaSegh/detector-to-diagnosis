# Exercise 3.5 notes

**Which policy where.**
- The *network receiver* faces hardware that will not wait. If the PC cannot keep up, data
  is lost somewhere; the receiver is the one place where loss is unavoidable, so it should
  be explicit there: drop the *newest* (incoming) data, count it, and report it.
- Stages *inside* the PC must use back-pressure (reject and wait). A drop in the middle of
  the pipeline is invisible to the hardware counters, and silently corrupts statistics such as
  count rates, dead-time corrections and randoms estimates.
- `drop_oldest` keeps the freshest data, which suits live displays and monitoring, not
  acquisition: it removes data that is already older than what follows and, for a time-ordered
  stream, creates a hole in the past that downstream consumers cannot detect without sequence
  numbers.

**Accounting.** Two invariants cover everything: every offered item is accepted, rejected or
dropped-newest; every accepted item is popped, evicted (dropped-oldest) or still queued.

**Gap detection.** `count_lost` is what a downstream stage runs on `Batch::sequence`. It
distinguishes loss (forward jumps) from duplicates or reordering (backward steps), which point
to different bugs.
