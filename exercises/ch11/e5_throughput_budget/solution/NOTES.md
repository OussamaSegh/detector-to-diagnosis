# Exercise 11.5: notes on the solution

**Where the numbers come from.** All from `measurements/ch11`, on the book's VM:
- 0.167 singles per decay: `countrate.txt`, no dead time, 16.7 M singles/s at 100 MBq of
  the NEMA-style line source in MiniDAQ's ring.
- Prompts of 1.346e-3 per Bq (trues and scatters: 89,100 + 45,500 per second at 100 MBq)
  plus 6.6e-12 per Bq² (randoms: 66,050 per second at 100 MBq). The randoms fit
  over-predicts at high activity, where the sorter's kill-all policy discards more
  multiples: 1.06 M/s predicted at 400 MBq against 0.92 M/s counted.
- 68 M singles/s for the pair stage: `bottleneck.txt`, where it is 97.5% busy at
  66.8 M singles/s.
- 16 bytes per coincidence, 5 M coincidences/s for the writer and 200 MB/s of disk are
  assumptions, to be replaced by the
  list-mode format of Chapter 12 and a measured disk.

**Results.** One Gigabit link is full at 14.79 M singles/s, which the source reaches at
88.6 MBq: the link is the bottleneck, as Chapter 9 predicted. With 10 GbE (147.9 M
singles/s, full at 886 MBq) the sorter is next, at 407 MBq, and with a 30% margin at
285 MBq. The disk, at 16 bytes per prompt, would not fill until about 1.3 GBq, where the
fits above no longer mean anything; it is not the bottleneck of this chain, but it is the
only stage whose load grows faster than linearly.

**A budget is only as good as its units.** The starter's "least capacity" picks the writer
in both chains: its 5 M is the smallest number, but it counts coincidences, about 2% of the
singles at 400 MBq, and the writer does not fill until about 774 MBq. Comparing
activities, which every stage shares, is what makes the stages comparable.

**Limits.** Each stage is assumed independent and its capacity fixed. On one machine the
sorter, the decoder and the writer share cores, caches and memory bandwidth, so the
capacities measured one stage at a time are upper bounds; `bottleneck.txt` measures them
together, which is why its 68 M is the number to use. The dead time of the front end
(Chapter 11's 1 µs per block) lowers every load at high activity, and moves the count-rate
peak, at about 100 MBq, below every saturation in this budget: the scanner's peak NECR is
set by the detector, not by this software, as long as one 10 GbE link carries the singles.
