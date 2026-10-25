# Exercise 11.5 (E): An end-to-end throughput budget

**Goal.** Put the chain's capacities side by side (readout link, sorter, writer, disk), each with a
load that grows with the activity in its own unit, and find which stage saturates first and
at which activity, with and without a safety margin. This is the plan's "write the
throughput budget from detector to disk".

**Time.** 1 hour.

**Starter.** `starter/budget.py` forgets the preamble and inter-frame gap that Chapter 9
counted, computes utilization upside down, adds the margin to the capacity instead of
keeping it free, and names as the bottleneck the stage with the smallest capacity, though
the capacities are in different units.

**Acceptance** (`tests/test_budget.py`, run by CTest as `ch11/e5_throughput_budget/...`):
- One Gigabit link carries 14.79 M singles/s at 182 words per packet, as in Chapter 9;
  10 GbE carries 147.9 M; four links carry four times one.
- A stage with load 2A and capacity 100 saturates at A = 50, and at 40 with a 20% margin;
  a stage whose load never grows never saturates.
- With the chapter's measurements and one Gigabit link, the link saturates first, at
  88.6 MBq, although the writer's capacity (5 M coincidences/s) is the smallest number.
- With 10 GbE the sorter saturates first, at 407.2 MBq, or 285.0 MBq with a 30% margin.
- The disk's load more than doubles from 200 to 400 MBq, because randoms grow as A².

**Then, by hand.** Add the stages the tests leave out: memory bandwidth for the sorter's
copies, the CPU of the writer once it compresses, a second sorter thread, a 10 GbE link per
half ring. Which stage is next after the sorter, and at which activity? Record the
assumptions next to each capacity in `NOTES.md`, as Chapter 3's budget did.

**Hints.** Utilization is load over capacity, and a margin is the share of the capacity you
keep free. Find the saturation of each stage on its own, then compare activities, which all
stages share, not capacities, which they do not.
