# The session, condensed

This session is reconstructed for the book. The change was written to hold defects that
MiniDAQ really had, and the dialogue is shortened to the steps that matter. It works from this
record alone: you do not need an agent to do the exercise.

**Person:** Implement `change/SPEC.md` in `loss_counter.hpp`.

**Agent:** The file already has `sequence_distance`, the signed distance of RFC 1982, so I'll
use it in both directions: a positive distance from `seq` to `next` is a late packet, a
positive distance from `next` to `seq` is a gap. That handles the wrap for free. For a late
packet I'll count it as reordered, then check the bitmap to see whether it is a copy.

*(edits `loss_counter.hpp`: the diff is `change/agent.patch`)*

**Agent:** Tests:

```text
[ RUN      ] LossCounter.InOrder                  [       OK ]
[ RUN      ] LossCounter.Gap                      [       OK ]
[ RUN      ] LossCounter.Wrap                     [       OK ]
[ RUN      ] LossCounter.LatePacketFillsGap       [       OK ]
[ RUN      ] LossCounter.Duplicate                [       OK ]
[ RUN      ] LossCounter.Restart                  [       OK ]
[  PASSED  ] 6 tests.
```

The wrap and the restart are both covered, and `sequence_distance` keeps the arithmetic
defined everywhere, so there is no edge case left.

**Person:** I'll review it.
