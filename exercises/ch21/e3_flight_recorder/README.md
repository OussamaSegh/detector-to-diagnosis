# Exercise 21.3 (H): A flight recorder that never shows half an event

**Goal.** Write the core of MiniDAQ's flight recorder yourself, for one writing thread: a ring of
the last 64 events that the writer fills without ever waiting, and a snapshot that any other
thread can take at any time and that holds only complete events. The tool is a seqlock per slot;
the difficulty is the memory order, and ThreadSanitizer checks it.

**Time.** 90 minutes.

**Starter.** `starter/tiny_recorder.hpp` and `.cpp`: the class with `record()` and `snapshot()`
to write, and a slot without the field a reader needs.

**Tasks.**
1. Give each slot a sequence word: odd while the writer writes the event, even when it is
   complete, and different for every event that uses the slot. Event `n` (from 1) writes
   `2n - 1`, then its fields, then `2n`.
2. `record()`: write the event into slot `(n - 1) % 64` with the orders that make a reader see
   the odd word before the fields change and the even word only after they are written. Publish
   `n` in `next_` last.
3. `snapshot()`: from the newest event back, copy a slot's fields between two reads of its
   sequence word, and keep the event only if both reads are `2n`. Stop at the first slot that
   was overwritten (every older one was too) and count it in `torn_`. Return the events oldest
   first.

**Acceptance** (`ch21/e3_flight_recorder/<variant>/...`): events in order, the last 64 after a
wrap, the newest few for a small snapshot, and a stress test in which a writer records while the
main thread takes thousands of snapshots: no event may have `b != ~a`. Run it in the `tsan`
preset too: a data race is a failure there even when the values come out right.

Then answer in `NOTES.md`: why are the fields atomics with relaxed order instead of plain
integers, and what would the fence in `snapshot()` prevent if you removed it?
