# Exercise 8.3 (M): The randoms rate, derived and measured

**Goal.** Derive the rate of random coincidences between two detectors that see
independent singles at rates S1 and S2 with a coincidence window `|t1 - t2| <= tau`, then
check the formula by counting chance pairs between two simulated, independent streams.
Estimate the randoms rate for two detectors at 1 M singles/s each with a 4 ns window.

**Time.** 1.5 hours.

**Starter.** `starter/randoms.cpp`: a generator of Poisson arrival times that works, a pair
counter that looks only forward in time, and a formula that is off by a factor.

**Acceptance** (`tests/test_randoms.cpp`):
- `expected_randoms_per_s(1e6, 1e6, 4e-9)` is 8000.
- `count_pairs_within` is exact on small hand-made streams, including pairs where the
  single in `b` comes first, pairs exactly `tau` apart, and one single in `a` matching
  several in `b`.
- For two independent streams of 1 M singles/s over 1 s and `tau` = 4 ns, the counted pairs
  are within 4 standard deviations of the formula (Poisson: the standard deviation of a
  count N is sqrt(N)).
- `count_pairs_within` runs in time proportional to the number of singles: 2 million
  singles in under a second in a debug build.

Write the derivation in `NOTES.md` in five lines or fewer.

**Hints.** Take a single in detector 1. How long is the interval in which a single in
detector 2 makes a pair with it, and how many singles of detector 2 fall in such an
interval on average?
