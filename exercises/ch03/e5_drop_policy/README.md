# Exercise 3.5 (M): Drop policies you can account for

**Goal.** When a bounded buffer is full, something has to give. Implement the three classic
answers in `ex::DropQueue<T>` and make every outcome countable, then implement the
downstream check that detects losses from sequence numbers.

**Time.** 90 minutes.

**Tasks.**
- `DropQueue<T>(capacity, policy)` with `push(T)` returning a `PushResult` and `pop()`:
  - `Policy::reject`: a full queue refuses the item (the caller decides to wait or retry:
    back-pressure);
  - `Policy::drop_newest`: a full queue discards the incoming item and counts it;
  - `Policy::drop_oldest`: a full queue evicts its oldest item, counts it, and accepts the new one.
- `stats()` returns accepted, rejected, dropped_newest, dropped_oldest and popped, such that
  `accepted == popped + dropped_oldest + size()` at every moment.
- `count_lost(seqs, first)`: given the batch sequence numbers a consumer received, in order,
  and the first expected number, return how many batches were lost. Duplicates or numbers
  going backwards are counted separately as `out_of_order`.

**Acceptance tests** (`tests/test_drop.cpp`): per-policy behavior, the accounting invariant
after a random sequence of 100,000 operations, and gap counting.

**Think about it** (answer in your notes): which policy should the network receiver of a PET
DAQ use, and which one must the stages inside the PC never use? What does `drop_oldest` do to
a time-ordered stream?
