# Exercise 24.4 (M): A counter wider than a register

**Goal.** Read a 64-bit counter that the board exposes as two 32-bit registers, while the board
keeps counting. A timestamp, an event counter and an uptime are all like this, and a naive read
returns, once in a while, a value 2^32 away from the truth: a timestamp 67 seconds off with a
64 MHz clock, or a count that went backwards.

**Time.** 45 minutes.

**Starter.** `starter/split_counter.hpp` and `.cpp`: it reads each half once.

**Tasks.** `read_counter`, as its comment says.

**Acceptance** (`ch24/e4_split_counter/<variant>/...`): a counter that does not carry, a carry
during the read at six different moments, a high half that never holds still, and a failed read.

**Then** answer in `NOTES.md`: firmware can make this problem go away with one flip-flop per bit.
How, and what must the interface control document then say about the order of the two reads?
