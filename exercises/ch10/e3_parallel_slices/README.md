# Exercise 10.3 (H): A parallel sorter that loses and doubles nothing

**Goal.** Split a time-ordered stream into slices, sort each slice on its own thread with
MiniDAQ's `CoincidenceSorter`, and join the results so that they are exactly what one
sorter would have produced: no coincidence lost at a slice boundary, none counted twice.
Then write down the argument that your cut rule is correct.

**Time.** 4 hours.

**Starter.** `starter/parallel_sorter.cpp` cuts the stream into equal pieces and sorts each
piece separately. A window that straddles a cut is split in two, the second piece opens
windows that the serial sorter never opened, and the last delayed windows of each piece are
cut short.

**Acceptance** (`tests/test_parallel_sorter.cpp`):
- On 10 ms of simulated data at 30 MBq, with kill all and take all goods, 1, 2, 3, 4 and 7
  threads give exactly the serial result, delayed coincidences included.
- On a dense synthetic stream, where gaps wider than the window are rare and rejected
  singles sit between accepted ones, 4 threads give the serial result, and every cut falls
  at a gap wider than the window between accepted singles.
- A pair that straddles the nominal middle, with a delayed partner in the second half, is
  found once.

The starter passes the first test. On realistic data, singles are about 170 ns apart and a
window is 4 ns, so an equal-size cut rarely lands inside a window or a delayed window: a
bug that shows up once in many runs, at a rate no one notices in a count. The other two
tests build exactly the cases that break it.

**Hints.** In fixed mode, which singles open windows depends on history. When does the
history stop mattering? A slice needs to see some singles beyond its end, but it must not
let them open windows: how do you tell its own coincidences from the ones that belong to
the next slice?

**Write-up.** Half a page: the cut rule, why it is correct, and what happens to your
speed-up when the stream has no gaps at all (a hot source, a very wide window).
