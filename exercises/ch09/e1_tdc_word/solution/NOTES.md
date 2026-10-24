# Exercise 9.1: notes on the solution

**The rule.** Keep the largest time code seen and the number of wraps. A new code more
than half the range *below* the largest one is a wrap: count it. A new code more than half
the range *above* the largest one is a late word from before the latest wrap: give it the
previous epoch. Anything closer than half the range is ordinary jitter in arrival order.
This is the same rule as `TimeUnwrapper` in `minidaq/format/packed_single.hpp`, and the same
serial-number idea as the packet sequence numbers of this chapter.

**Why the starter fails.** "Any step back is a wrap" is right only for a perfectly ordered
stream. One word that arrives 5 µs late adds 94 minutes to every later timestamp. Nothing
crashes, and every coincidence after that point is lost, because the channel's times are
no longer comparable with the others. The type check is the other quiet failure: a status
word decoded as a hit is a hit at a random time on a random channel.

**What a real decoder adds.** Fine-time calibration (real TDC bins are uneven, so each
fine code maps to a measured time through a table), per-channel time offsets, and a check
that the decoded time is plausible (not far from the last one) as a detector of corrupted
words.
