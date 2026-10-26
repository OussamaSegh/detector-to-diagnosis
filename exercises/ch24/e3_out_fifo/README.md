# Exercise 24.3 (M): The board's output FIFO, cycle by cycle

**Goal.** Write the output FIFO of the front-end board as a cycle model, the way a software
engineer checks a firmware design: from its specification, against a plain reference, on the
same stimulus as the firmware's own testbench. Then compute how long the FIFO takes to fill and
to drain, and how deep it must be for a burst.

**Time.** 60 minutes.

**Read first.** `hw/rtl/feb_out_fifo.sv` (Chapter 24) and its testbench; the model must do what
the listing does at each rising edge.

**Starter.** `starter/out_fifo.hpp` and `.cpp`.

**Tasks.** `OutFifo::clock`, `time_to_full_s`, `drain_time_s` and `depth_for_burst`.

**Acceptance** (`ch24/e3_out_fifo/<variant>/...`): order and refusal when full (also when the
link takes a word in the same cycle), nothing while the triggers are off, set wins over clear, the
plain model on 20,000 cycles of random traffic, and the chapter's numbers.

**Then** answer in `NOTES.md`: the board drops the new event when the FIFO is full. Why not
the oldest word instead, and why is the overflow flag a lower bound of the loss?
