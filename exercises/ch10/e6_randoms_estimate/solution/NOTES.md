# Exercise 10.6: notes on the solution

**The factor of two.** A single in detector 1 at time t pairs with any single in detector 2
in [t − τ, t + τ]. That interval is 2τ long, so the expected number of partners is 2τ S2
(for 2τ S2 ≪ 1, which at 1 M/s and 4 ns is 0.008), and the random rate is 2τ S1 S2. The
starter's one-sided count and its τ S1 S2 are wrong by the same factor of two and agree
with each other perfectly, which is why a hand-made case is part of the tests.

**Why the singles estimate survives trues.** A true pair adds one single to each detector,
and those singles make random pairs with everything else exactly like background singles
do. The formula counts singles, not "background", so it includes them. What it does not
count is the true pair itself, which is what the prompts minus the delayed count measure.

**MiniDAQ's one-sided window.** The sorter opens a window at the earlier single and looks
forward by τ. Between two detectors, a pair with detector 2 first is found from detector
2's single, a pair with detector 1 first from detector 1's: together they cover |Δt| ≤ τ,
the same 2τ.

**Limits.** The formula assumes independent detectors and no dead time. With multiples
handling, sorter dead time and per-crystal rates, a real scanner's randoms are estimated
per line of response from per-crystal singles rates (verify: Oliver and Rafecas, PLoS ONE
2016, compare the delayed window, singles-based and singles-prompts methods, and their
biases), and the delayed window of `measurements/ch10/validation.txt` differs from the
true randoms by up to about 8% depending on the multiples policy.
