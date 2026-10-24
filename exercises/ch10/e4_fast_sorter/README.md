# Exercise 10.4 (H): Reach the throughput target

**Goal.** The starter is a coincidence sorter that is correct and slow. Make it at least
twice as fast, and fast enough for 30 M singles per second on one core (singles inside the
energy window: rejecting the others costs one comparison each), without changing a single
coincidence it finds. Then write a one-page performance report.

**Time.** 4 hours, plus the report.

**Starter.** `starter/fast_sorter.cpp` is the baseline of `tests/baseline_sorter.hpp`,
written the obvious way: a `std::deque`, two `std::vector`s built for every window, a
`std::function` for every coincidence, the crystal positions computed with `cos` and `sin`
for every pair, `std::hypot` and a division for the field-of-view distance.

**Acceptance** (`tests/test_fast_sorter.cpp`):
- For all four multiples policies, with and without the delayed window, with a 120 mm field
  of view, and with the input in random chunks: exactly the coincidences of MiniDAQ's
  `CoincidenceSorter`, in the same order (the baseline passes this too).
- `FastSorter.FastEnough` (release builds without sanitizers): at least twice the
  baseline's singles per second on 20 ms of simulated 20 MBq data, and more than 30 M
  singles/s inside the energy window (best of five runs). `EX_MIN_SPEEDUP` and
  `EX_MIN_SINGLES_PER_S` override the two limits on a machine where you have measured a
  reason to.

**Report** (one page, in your NOTES): the machine, compiler and flags; the profile before
(where the time went, with numbers); each change and what it bought, measured one at a
time; the result with its spread over repetitions; what you would try next.

**Hints.** Profile first (Chapter 5): which line costs the most may surprise you. Which of
the baseline's costs are paid per single, which per window, which per pair? How many
singles does the buffer hold at 20 MBq?
