# Task given to the agent

Finish `LossCounter::offer` in `loss_counter.hpp`. Sequence numbers are 32 bits and wrap from
2^32 - 1 to 0. Let `next` be the number expected after the newest one received.

1. **In order** (`seq == next`): nothing lost.
2. **A gap** (`seq` ahead of `next` by up to `max_gap`): the numbers skipped are lost.
3. **A late packet** (`seq` behind `next` by at most `window`): if that number was never
   received, it fills its gap: one fewer lost, one more reordered ("arrived after a higher
   sequence number, and filled its gap"). If it was received already, it is a copy: stale, and
   nothing else. Each packet counts in one category.
4. **A restart.** A packet more than `max_gap` ahead, or more than `window` behind, means the
   link restarted its numbering (a board reset): count a resync, lose nothing, and follow the
   new numbering. Serial arithmetic cannot say whether a packet exactly 2^31 away is ahead or
   behind; it is a restart too, never a loss.

The counters are how the operator judges a scan's completeness (SRS-RDO-006). Add tests.
