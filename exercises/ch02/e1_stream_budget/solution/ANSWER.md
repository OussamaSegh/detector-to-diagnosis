# Answer

| Record size | Bytes/s | GiB/s | Gbit/s | Records per 64 B line |
|---|---|---|---|---|
| 8 B (packed MDQ-P1 word) | 240 MB/s | 0.224 | 1.92 | 8 |
| 12 B | 360 MB/s | 0.335 | 2.88 | 5 (and records straddle lines) |
| 16 B (`minidaq::Single`) | 480 MB/s | 0.447 | 3.84 | 4 |

What the numbers mean:
- **Network.** 1.92 Gbit/s of payload does not fit a 1 GbE link at all; it fits 10 GbE with
  room for headers (Chapter 23). Unpacked 16-byte records need 3.84 Gbit/s plus framing.
  This is why front-end boards send packed words.
- **Memory.** Every pipeline stage that copies the stream reads and writes it: 0.45 GiB/s
  per pass for 16-byte singles. A modern DDR4/DDR5 channel sustains tens of GiB/s, so a
  handful of passes is fine; the risk is not bandwidth but cache misses on random access
  (sorting, histogramming), which cost latency per event.
- **Disk.** 240 MB/s of singles is about 0.86 TB per hour. A single SATA SSD sustains a
  few hundred MB/s of sequential writes; an NVMe drive several GB/s. This is one reason
  scanners usually store coincidences (list mode), not singles: the coincidence rate is a
  small fraction of the singles rate (Chapter 11).
- **12-byte records** do not divide 64, so some records straddle two cache lines; a 12-byte
  struct with an `int64_t` member would also be padded to 16 bytes by the compiler unless
  packed, which costs unaligned access. Sizes that divide the cache line are simpler.
