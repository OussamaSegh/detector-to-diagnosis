# Exercise 23.1: notes on the solution

**Why the first layer.** A datagram that a layer drops never reaches the layers after it, so a
drop upstream can hide a problem downstream, but never the other way round. A card that misses
frames because its ring is too small also makes the backlog and the socket look quiet. Fix the
first layer that drops, measure again, and only then look at the next one: the numbers after the
first drop describe a load that the system will not see once the first problem is fixed.

**Why "unknown" is not zero.** A report that says `nic: 0` when it could not read the card's
counters tells the reader that the card dropped nothing, which nobody measured. The same rule is in
MiniDAQ: a counter it cannot read is left out of the status rather than reported as zero
(SRS-RDO-014).

**The host's counter and the socket's.** `RcvbufErrors` counts every socket of the host; the
socket's drops column counts one. On a DAQ PC that runs only the acquisition they should agree; a
difference means another program on the same host is losing datagrams, which can be a sign that it
competes for the same CPUs.

**Wrapping.** The softnet counters and the socket's drop count are 32-bit. At 500,000 packets per
second, `processed` wraps in under 2.5 hours, so a report over a long run must subtract modulo
2^32, and a run long enough for a counter to wrap twice between readings needs more frequent
readings.
