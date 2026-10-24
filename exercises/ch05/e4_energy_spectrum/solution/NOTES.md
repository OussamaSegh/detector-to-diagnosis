# Exercise 5.4 notes

**Measured** (book's machine, GCC 13.3 -O2, pinned, 1 Mi codes per iteration, medians of 5):

| Codes | simple | split (4 sub-histograms) |
|---|---|---|
| uniform over 2,048 bins | 2.10 G/s | 2.26 G/s |
| 511 keV photopeak, sigma 25 keV (50 codes) | 2.06 G/s | 2.11 G/s |
| one constant code | 0.41 G/s | 1.24 G/s |

**Why.** `++h[c]` is a load, an add and a store. If the next code hits the same bin, its load
must wait until the previous store's value is available (store-to-load forwarding, several
cycles). A run of identical codes therefore forms one long dependency chain, and the loop runs
at the forwarding latency instead of at the throughput of loads and stores. With four
sub-histograms, four consecutive increments of the same code go to four different counters:
four independent chains, so the core overlaps them. A real photopeak spreads over about 50
codes at sigma 25 keV, so consecutive repeats are rare and both versions run near 2 G/s. The
constant code is what a stuck channel, a saturated ADC or a test pulser produces: rare, but it
is exactly when you do not want the monitoring to fall behind.

**Counter width.** Four arrays of 32-bit counters (32 KiB) fit in L1 next to the input
stream; 64-bit counters would double that. 32 bits are safe per call as long as one call adds
fewer than 2^32 codes to one bin, and the merge adds them into 64-bit totals, which the last
test checks.
