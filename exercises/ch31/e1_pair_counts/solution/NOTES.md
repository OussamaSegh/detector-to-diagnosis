# Exercise 31.1: notes

The starter makes three mistakes, each of which the tests show:

1. It keys a pair by (earlier crystal, later crystal). The same line of response appears under two
   keys, one for each order of arrival, about half of its counts under each: an ordered key
   splits every pair.
2. It counts the delayed coincidences, whose crystal_a carries bit 15: their keys are beyond the
   scanner (crystal_a + 32,768), and they are randoms, not prompts.
3. It counts tags (crystal_a 0x7FFF), whose crystal_b is a tag kind, not a crystal.

It also reads the whole file into memory with `np.fromfile`. That is not a wrong answer, so no
test fails for it; the memory test with a file larger than the limit set for the test would be
slow, and the chapter measures the difference instead (measurements/ch31, section 1).

By hand:

1. `np.memmap` returns at once: it maps the file and reads nothing. The time is spent in the
   first arithmetic on the records (`a & DELAYED_BIT`), where the pages are read.
2. The view `m[...].view(RECORD)` is valid because the block's records start at a multiple of 8
   bytes from the start of the file (MDQ-L1 section 3.1 pads the header) and RECORD has no
   padding: 16 bytes, little-endian fields, the layout on disk.
3. A dense matrix of 18,432 x 18,432 int64 counts would take 2.7 GB; a point source touches
   tens of thousands of pairs (the QC report's `pairs_hit` for a 2-second run of the simulator's
   point source).
