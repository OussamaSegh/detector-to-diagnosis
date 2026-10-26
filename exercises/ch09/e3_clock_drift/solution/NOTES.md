# Exercise 9.3: notes on the solution

**The correction.** Sync pulse k happens at global time k·T and board A stamps it at
local time L_k. Between two pulses the clock runs at a constant rate to a very good
approximation, so a local time l with L_k ≤ l < L_{k+1} maps to
global = (k + (l − L_k) / (L_{k+1} − L_k)) · T. This piecewise linear map removes the offset,
the drift, and slow changes of the drift (a crystal oscillator's frequency follows its
temperature), to within the jitter of the sync stamps. The starter removed only the
offset, so its error grew by 20 µs per second.

**How often to sync.** For a constant drift, two stamps are enough in principle: the test
with one pulse per second passes. Real drift changes with temperature on the scale of
seconds to minutes, and the sync stamps carry jitter. More frequent pulses follow the
changes, at the cost of more marker words in the data. Many systems avoid the problem
instead: they distribute one reference clock to all boards, so the boards cannot drift
apart, and use sync pulses only to align the counters at the start (verify: your scanner's
clock distribution with the team).

**From the data alone.** True coincidences have a real time difference that averages
to zero over the field of view. The slope of tB − tA against tA is therefore the relative
rate of the two clocks: −20 ppm here. The statistical error of the slope is
σ_d / (√n · σ_t): 141 ps / (√40,000 · 0.58 s) ≈ 1.2 × 10^−12, a millionth of a ppm, so
the test's 0.05 ppm tolerance is generous. This is the answer to the chapter's
check-yourself question: a board drifting by 1 ns per second (1 ppb) moves its
coincidence time peak by 1 ns per second, far more than the peak's own width of a few
hundred ps after a few seconds, so a histogram of tB − tA per one-second slice shows it at
once. In a real scanner, randoms add a flat background under the peak, so fit the peak
position per time slice rather than a straight line through every pair.
