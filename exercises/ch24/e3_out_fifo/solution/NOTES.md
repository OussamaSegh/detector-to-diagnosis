# Exercise 24.3: notes on the solution

**State before the edge.** Every decision of a clock edge (push, pop, the flag) is computed from
the state before it, then applied together. Written in that order, the model cannot accidentally
let a pop make room for a push in the same cycle, which the listing does not do either: `full` is
the old count. Allowing it saves one word of capacity and costs a longer path in the logic; the
firmware team chose the simpler one, and the model must follow the firmware, not improve it.

**Drop the new event.** Dropping the oldest word would hide the loss inside the data: a stream
with a hole in its middle, a sequence of datagrams that no longer matches what was measured, and a
receiver that cannot tell. Dropping the new event keeps everything already accepted intact and in
order, and the loss is at a known place, counted by a flag. In a PET scanner, a lost single is a
lost count; a corrupted one is a wrong count, which is worse.

**A lower bound.** The flag is sticky and one bit wide: between two reads by software, one lost
event and ten thousand look the same. MiniDAQ counts the cycles in which it found the flag set,
which is at least the number of overflow episodes, and treats any as a loss of the run. A firmware
that must report how much was lost needs a counter register, which is a change to the interface
control document (ICD-FEB section 8 lists the sent-datagram counter for the same reason).

**Sizing.** Depth is the excess rate times the burst: `(in - out) * burst`. A FIFO only absorbs
bursts; if the average rate in is above the rate out, no depth is enough, and the time to fill is
all you can compute.
