# Exercise 9.2 (M): Counting loss and reordering on a link

**Goal.** A readout board numbers its packets with a 16-bit counter. Write a monitor that
watches the sequence numbers of one link and counts lost, reordered and duplicated packets,
without holding any packets back. Check it against the MiniDAQ fault injector
(`minidaq/sim/readout_link.hpp`) at 0.1% loss and 0.2% reordering, over enough packets for
the counter to wrap several times.

**Time.** 1.5 hours.

**Starter.** `starter/link_monitor.cpp` counts gaps as losses. It knows nothing about late
packets or duplicates, and it computes the gap as an unsigned number.

**Acceptance** (`tests/test_link_monitor.cpp`):
- Clean link: nothing counted. A gap of two: two lost.
- A packet that arrives late fills its gap: it counts as reordered, not lost.
- Duplicates are counted, whether the copy follows at once or comes much later.
- The wrap from 65535 to 0 is neither loss nor reordering, and a gap across it is counted
  correctly.
- Over 200,000 packets through the fault injector, the monitor's counts equal the
  injected losses, delays and duplicates exactly.

**Hints.** What does `static_cast<std::uint16_t>(seq - highest)` look like for a packet
one behind? To tell a late packet from a duplicate, you need to remember which recent
sequence numbers you have seen: how many is enough?
