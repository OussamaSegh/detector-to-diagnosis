# Exercise 19.1: notes on the solution

The key is the delayed packet that comes too late. The tracker holds a gap for a limited number of
packets and a limited time; when it gives up, it counts the sequence number as lost and moves on.
When the packet then arrives, its number was already declared lost, so the packet is stale and is
dropped. One delayed packet is in two counters: its number in `packets_lost`, the packet itself in
`packets_stale`. The number of such packets is not reported by anyone, but it follows from the
others: `delayed - reordered`. With it, the lost and stale identities are exact.

A packet that was delayed and duplicated is the trap: its copy went on time, so the late original
is a duplicate (stale), not a late packet, and subtracting it from the delayed count is what makes
the heavy recording balance. MiniDAQ's own system test missed it at first (MDQ-PR-018): at 1% of
each kind of damage the overlap is rare, and the recording it used had none.

The heavy recording (5% of each kind of damage) has packets that came too late and packets that
were both; without them, a check that ignored either would pass every recording. That is why the
tests require them.

If the server dropped a received datagram before the tracker saw it, `datagrams` would still
hold (the datagram arrived) and `received` would too (the tracker never saw it, so it is in
neither `packets_received` nor the delivered or stale counts). The tracker would see a gap and
declare the sequence number lost, so `lost` breaks: one more loss than the sender injected and the
late packets explain. The difference `datagrams - packets_received` (with no rejected datagrams)
would also show it, which is why the server counts datagrams and packets separately.
