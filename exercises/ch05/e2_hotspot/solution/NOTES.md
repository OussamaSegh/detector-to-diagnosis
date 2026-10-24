# Exercise 5.2 notes

**Profile of the starter** (book's machine, `perf record -e cpu-clock`, release build): the
standard distributions dominate: `std::normal_distribution` (Marsaglia's polar method, with a
rejection loop and a log and a square root per pair), the `log` behind
`std::exponential_distribution`, `std::mt19937_64` (a 2.5 KiB state refreshed in bulk), and
`std::uniform_int_distribution`, which may divide.

**Changes and what each bought** (singles per second, `bench_source`, pinned, medians):

| Version | M singles/s | ns per single |
|---|---|---|
| starter | 18.7 | 53.5 |
| xoshiro256** generator, Lemire multiply-shift for crystals, polar method kept | 44.0 | 22.7 |
| normal quantile table with interpolation, series log for the gaps | 74.7 | 13.4 |

The remaining profile is the generate loop itself: the pairing decision is a branch taken 30%
of the time at random, which the predictor cannot learn, and every primary still needs one
logarithm (now inline arithmetic).

**What it costs.** The quantile table clips the normal distribution at about 3.67 sigma
(0.024% of samples), and the series logarithm has a relative error below 1e-6. Both are fine for
a test source; neither is acceptable for the detector simulator of Chapter 8, where the energy
spectrum's tails (scatter, pile-up) are the point. xoshiro256** is a good general-purpose
generator, but not a cryptographic one: never use it for anything security-related.

**Method.** One change at a time, measured each time, with the statistical tests run after
each change. The intermediate version (row two) kept `std::log` for the gaps and the polar
method for energies; its profile then showed the polar method (38% of samples) and `log`
(27%) as the next targets, which is what the last row removes.
