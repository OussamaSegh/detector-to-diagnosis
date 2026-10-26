# Exercise 24.2 (E): Gray code across clock domains

**Goal.** Encode and decode Gray code, and compute how many words the read side of an
asynchronous FIFO may read from a write pointer that crossed into its clock domain in Gray code.
Firmware teams use this every day; you will meet it in their designs and in their bugs.

**Time.** 30 minutes.

**Starter.** `starter/gray_code.hpp` and `.cpp`.

**Tasks.** `encode`, `decode`, `bits_changed` and `readable`, as their comments say.

**Acceptance** (`ch24/e2_gray_code/<variant>/...`): known values, decode undoes encode, one bit
per step also at the wrap, a sample taken while the pointer changes is the old or the new value,
and the readable count with wrapped pointers.

**Then** answer in `NOTES.md`: why does a synchronizer of two flip-flops make a single bit safe to
read in another clock domain, but not a binary counter, and why is a write pointer that arrives a
cycle late harmless to the read side?
