# Exercise 24.4: notes on the solution

**Why high, low, high.** The counter moves between any two bus accesses. If the high half is the
same before and after the read of the low half, no carry happened while the low half was read,
so the low half belongs with that high half and the pair is a value the counter held. If the high
half changed, a carry happened somewhere in between and the low half may belong to either; try
again. A counter whose high half changes at every access (a fast counter on a slow bus) never
gives a consistent pair, so the attempts are bounded and the failure is reported, not hidden.

**Low then high is wrong.** Reading the low half just before it wraps (0xFFFFFFFF) and the high
half just after the carry gives a value almost 2^32 too large. Reading high then low the other way
round gives one 2^32 too small. Either way, once every 2^32 counts: rare enough to pass every test
that does not aim at it.

**The firmware's fix.** A read of the low half copies the high half into a shadow register in the
same clock cycle, and a read of the high register returns the shadow. One read of each then gives
a consistent pair, but only in that order: low first, then high, with nothing else reading the
low half in between (another thread, or an interrupt handler). The ICD must say so, because it
is a rule for every program that reads the counter. A 64-bit bus access, where the hardware
supports it, is the other way out.
