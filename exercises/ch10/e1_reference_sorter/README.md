# Exercise 10.1 (M): A reference sorter, checked against the truth

**Goal.** Write the simplest correct coincidence sorter: fixed windows, multiples
discarded, an energy window. Return the coincidences as indices into the input, so that
you can classify each one with the simulator's ground truth as a true, a scatter or a
random. This is the reference that every faster sorter is compared with.

**Time.** 2 hours.

**Starter.** `starter/reference_sorter.cpp` pairs every single with the next one if it is
close enough. It has no energy window, it lets the third single of a window form another
pair, and `classify` calls everything a true.

**Acceptance** (`tests/test_reference_sorter.cpp`):
- Hand-made streams: the window is inclusive; three singles in a window give nothing; the
  single after a window opens the next one; a single outside the energy window takes no
  part.
- At 10 MBq for 50 ms of simulated time, your trues, scatters and randoms equal those of
  the Chapter 8 truth counter exactly, and your pairs are exactly the ones MiniDAQ's
  `CoincidenceSorter` finds with the same rules.

The plan for this chapter asked for agreement with the truth "within 0.5%". With the same
window rules there is no reason for any difference at all: a single extra or missing pair
is a bug, and an exact test finds it where a tolerance would hide it.

**Hints.** Filter by energy before you form windows, not after: why does the order
matter? After a window closes, where does the next one open?
