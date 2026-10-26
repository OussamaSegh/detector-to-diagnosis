# Exercise 9.5: notes on the solution

**The overhead.** A UDP datagram with p bytes of payload occupies p + 8 (UDP) + 20 (IPv4)
+ 14 (Ethernet header) + 4 (frame check sequence) bytes as a frame, padded to at least 64,
plus 8 bytes of preamble and start-of-frame delimiter and a 12-byte inter-frame gap: 66
bytes beyond the payload for every frame that is not padded. The MDQ-R1 header adds 16.
With 182 words a single costs 8.45 bytes on the wire, 6% more than its 8 bytes of data.

**What it means.** One Gigabit link carries at most 14.8 M singles/s in full standard
frames, 67.6% full at 10 M singles/s. That leaves too little margin for a high-activity
scan (Chapter 11), so a scanner of that class uses 10 GbE links, several links, or
on-board coincidence filtering (verify: your scanner's link type and count with the team).
Small packets are expensive: at 32 words per packet the overhead is 32%, and the packet
rate, which costs the receiving CPU per packet, is 5.7 times higher.

**Jumbo frames.** With a 9000-byte MTU a packet can hold over a thousand words (MDQ-R1
allows up to 1024), and the overhead per single drops below 1%. The price is latency per
packet and the need for every switch and NIC on the path to be configured for it.
