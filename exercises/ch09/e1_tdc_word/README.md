# Exercise 9.1 (M): Decoding a TDC word with rollover

**Goal.** Write a decoder for a made-up 64-bit front-end word: a 4-bit type, a 10-bit
channel, a 40-bit coarse time and a 10-bit fine time. The coarse counter ticks every
5.12 ns, and the fine time divides a tick into 1024 bins of 5 ps. The 50-bit time code wraps
every 2^40 coarse ticks (about 94 minutes, so a long scan crosses it). The decoder must
return absolute times across wraps, and words may arrive a few microseconds late.

**Time.** 1.5 hours.

**Starter.** `starter/tdc_word.cpp` gets the fields right. It treats every word as a hit,
and it counts any step backwards as a wrap.

**Acceptance** (`tests/test_tdc_word.cpp`):
- Channel and time are decoded with the right units, and the largest time code does
  not overflow.
- Words of other types are skipped and counted.
- A wrap is undone exactly: one tick across the wrap is one tick.
- A word that arrives 5 µs late is earlier than its predecessor, not 94 minutes later.
- A late word from just before a wrap, arriving after the wrap, gets the earlier epoch.
- 2.9 hours of hits are monotonic, with exactly one wrap.

**Hints.** Two time codes that are less than half the range apart are close in time,
whichever order they come in. What does the difference look like when one of them is just
after a wrap?
