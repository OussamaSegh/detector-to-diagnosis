# Exercise 9.5 (E, extra): A link budget

**Goal.** Work out how many singles per second one Gigabit Ethernet link can carry in
MDQ-R1 packets, and how the packet size changes that. Count every byte a frame occupies
on the wire, not only the payload.

**Time.** 30 minutes.

**Starter.** `starter/link_budget.py` counts the payload and the IP and UDP headers, and
nothing else.

**Acceptance** (`tests/test_link_budget.py`):
- A packet of 182 words is a 1472-byte UDP payload and occupies 1538 bytes of wire time;
  a 1-byte payload is padded to the 64-byte minimum frame and occupies 84 bytes.
- With 182 words per packet, a single costs 8.45 bytes on the wire, and one link carries
  14.8 M singles/s at 1 Gbit/s or 148 M singles/s at 10 Gbit/s.
- With 32 words per packet, a single costs 10.56 bytes and the 1 Gbit/s limit falls to
  11.8 M singles/s.
- 10 M singles/s with 182 words per packet use 67.6% of a Gigabit link, in 54,945 packets
  per second.

**Hints.** Look up what an Ethernet frame consists of on the wire: what comes before the
destination address, what follows the payload, and what must separate two frames.
