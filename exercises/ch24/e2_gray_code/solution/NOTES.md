# Exercise 24.2: notes on the solution

**Decode.** Each binary bit is the XOR of all Gray bits at and above it. Folding the word onto
itself with shifts of 1, 2, 4, 8 and 16 computes that prefix XOR in five steps instead of 32.

**One bit and many.** A flip-flop that samples a signal changing at the same moment can go
metastable and settle to either value, late. A second flip-flop gives it a full clock period to
settle, which makes a wrong *timing* very unlikely, but it does not decide *which* value is
caught: old or new. For one bit either is a correct reading of a moment. For a binary counter,
each changing bit is caught old or new independently, so going from 7 to 8 (four bits change)
can be read as any of 16 values, 14 of them never held. Gray code changes one bit per step, so any
sample is the old or the new value.

**Late is safe.** The read side compares the synchronized write pointer with its own read pointer.
A pointer that arrives one or two cycles late is an old value, so the read side believes the FIFO
holds fewer words than it does: it waits a little longer and never reads a word that is not yet
written. The same holds on the write side with the read pointer: it believes the FIFO fuller than
it is. Pessimism in both directions is what makes the design safe.

**For software.** The same problem appears on the bus: a 64-bit counter exposed as two 32-bit
registers can change between the two reads (Exercise 24.4), and a register that firmware updates
from another clock domain must be designed to be read at any moment; ask the firmware team how.
