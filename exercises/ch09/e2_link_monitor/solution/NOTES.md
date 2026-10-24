# Exercise 9.2: notes on the solution

**Signed distance.** `int16_t(uint16_t(seq - highest))` is the distance from the highest
sequence number seen to the new one, correct across the wrap as long as the two are less
than 32,768 apart. The starter's unsigned gap turns "one behind" into 65,535 lost
packets: one late packet, and the loss counter is ruined for the run.

**Counting without holding.** A monitor cannot wait to see whether a gap fills, so it
counts the gap as lost when it appears and takes it back if the packet turns up. The
counts are then right at any moment, up to packets still on their way, and exact at the
end. A bitmap of the last 1,024 sequence numbers tells a late packet (bit clear) from a
duplicate (bit set). 1,024 is far more than any reordering a switch produces. Packets
further behind are counted as duplicates: at that distance nothing can be known.

**MiniDAQ's tracker is different on purpose.** `readout::SequenceTracker` must hand words
on in order, so it holds early packets and must decide, after a hold time, that a gap is
lost. This monitor only counts. In a real system you might want both: a monitor in the
firmware or NIC for diagnostics, and a tracker in the DAQ for the data.

**The fault injector's numbers.** With delays of at most 8 positions and no duplicates,
every delayed packet is reordered once, and every dropped one is lost. The test checks
equality, not "close": a counter that is off by one on a known input is a bug.
