# Exercise 21.3: notes on the solution

**Why atomics for the fields.** A reader copies a slot while the writer may be writing it. With
plain integers that is a data race, and a data race is undefined behavior in C++ even if the
reader throws the value away afterwards: the compiler may assume it does not happen, and
ThreadSanitizer reports it. Relaxed atomics make each load and store indivisible and cost
nothing on x86-64 and little on AArch64 for aligned 64-bit words; the sequence word gives the
ordering. This is the seqlock as the C++ memory model allows it (see the paper by Boehm in the
chapter's references).

**The orders.** The writer stores the odd word, then a release fence, then the fields, then the
even word with release. The reader loads the word with acquire, then the fields, then an acquire
fence, then the word again. The first pair makes a reader that sees a field of the new event see
the odd word too, on its second load; the second pair makes a reader that sees the even word see
the fields that came before it.

**Without the fence in `snapshot()`.** The two relaxed loads of the fields could be performed
after the second load of the sequence word. The check would then compare two values read before
the copy, find them equal and even, and keep fields that the writer changed afterwards: a torn
event, `b != ~a`, which is exactly what the stress test looks for. On x86-64 the hardware keeps
loads in order, so the test may pass there anyway; the compiler may still reorder, and on AArch64
the processor may too. TSan does not see a missing fence between atomics, which is why the
reasoning has to be written in the comments.

**Why stop at the first overwritten slot.** The writer fills the slots in order, so if the slot
of event `e` holds a newer event, every older slot does too: going on would only count more
torn events.
