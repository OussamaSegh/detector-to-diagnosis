# Exercise 10.6 (E): Randoms from the singles rates

**Goal.** For two independent detectors with singles rates S1 and S2 and a coincidence
window τ (a pair counts if the two singles are at most τ apart, either one first), the
random coincidence rate is R = 2τ S1 S2. Derive it, then check it against simulated
streams: with independent singles only, and with true pairs added, where it must agree
with the delayed-window estimate.

**Time.** 1 hour.

**Starter.** `starter/randoms.py` uses τ S1 S2, and its pair counter only looks for
detector 2 after detector 1. Both mistakes halve the answer, so they agree with each other
and are both wrong: the tests compare them with a hand count, not only with each other.

**Acceptance** (`tests/test_randoms.py`, run by CTest as `ch10/e6_randoms_estimate/...`):
- The formula: 8,000 randoms/s for 1 M singles/s in each detector and 4 ns.
- A hand-made case: a partner 3 ns before and one 4 ns after are counted, 5 ns is not, in
  both directions.
- 0.5 s of independent Poisson streams at 1 M/s and 0.8 M/s: the prompt and the delayed
  counts both agree with 2τ S1 S2 within four standard deviations.
- With 200,000 true pairs per second added: prompts minus delayed equals the number of
  trues, and the delayed count agrees with the singles-based estimate.

**Hints.** For one single in detector 1, how long is the interval in which a single in
detector 2 would make a pair? Why does the singles-based estimate stay right when trues
are added, even though every true adds one single to each detector?

**Afterwards.** MiniDAQ's sorter sees one merged stream and opens its window only after
the earlier single. Why does it still find pairs in both orders between two detectors, and
so match 2τ rather than τ?
