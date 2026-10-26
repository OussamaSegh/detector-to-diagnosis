# Exercise 24.1 (M): Check a valid/ready handshake

**Goal.** Read a recorded stream, cycle by cycle, and say how many words moved, how long the
receiver pushed back, and which rule of the handshake was broken where. A firmware engineer who
says "the link drops words" will show you a waveform; this is how you read one with them.

**Time.** 45 minutes.

**Starter.** `starter/handshake.hpp` and `.cpp`.

**Tasks.** `check`, as the header's comment says: count transfers, stalls and idle cycles, the
longest run of stalls, and report every violation of rules 2 and 3 as `"cycle N: ..."`.

**Acceptance** (`ch24/e1_handshake/<variant>/...`): back-to-back words, ready without valid, a
valid dropped before its transfer, data changed while waiting, and the longest back-pressure.

**Then** answer in `NOTES.md`: rule 4 says that a sender must not wait for ready before it raises
valid. What happens when both sides wait for the other, and why can one trace not show that a
design breaks the rule?
