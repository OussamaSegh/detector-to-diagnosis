# Exercise 10.3: notes on the solution

**Why a gap is a safe cut.** In fixed mode a window opened at time t takes every accepted
single up to t + window. If two consecutive accepted singles are more than a window
apart, the window that holds the first cannot hold the second, so the second always opens
a new window, whatever happened before. Everything after such a gap is sorted exactly as
it would be by a sorter that started there. The cut rule takes the first such gap after
each nominal boundary. Singles outside the energy window are ignored by the sorter, so
the gap is measured between accepted singles: a rejected single in the middle of a pair
does not separate it.

**Read-ahead without double counting.** The delayed window of an opener at t reaches
t + delay + window, which can be in the next slice. Each worker therefore also sorts the
singles up to that time beyond its end, and then drops every coincidence whose first
single (its opener) is at or after the next slice's first single: those belong to the
next worker, which finds them itself. Because the cut is at a strict gap, "first single at
or after the cut" is unambiguous.

**Order.** Each slice's coincidences come out in opener order, and slices are joined in
time order, so the joined list is in the serial order and can be compared with `==`.

**When it does not help.** If the stream has no gap wider than the window (per-crystal
rates high enough, or a very wide window), there is nowhere to cut and the work stays on
one thread: `slice_starts` returns fewer slices than threads. In the simulator at 30 MBq
about 6 M singles/s pass the energy window (`measurements/ch10/validation.txt` has 4.0 M/s
at 20 MBq and 8.0 M/s at 40 MBq), a mean spacing of about 170 ns against a 4 ns window, so
gaps are everywhere. Check the real scanner's singles rates before relying on this.
Per-single windows have no history at all: any cut works, with the same read-ahead.

**Cost.** The read-ahead sorts up to delay + window of extra data per slice, 104 ns here,
which is negligible for slices of milliseconds.
