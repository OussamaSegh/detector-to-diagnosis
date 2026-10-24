# Exercise 5.4 (M, extra): An energy spectrum, fast

**Goal.** Every PET DAQ histograms energies: for the operator's spectrum display, for energy
calibration (Chapter 11) and for quality control. Histogramming looks trivial and has a
surprising performance trap. Implement it twice and measure where the trap is.

**Time.** 90 minutes.

**Tasks.**
1. `ex::fill_simple(codes, h)`: add each 11-bit energy code to the 2,048-bin spectrum.
2. `ex::fill_split(codes, h)`: the same result, using four sub-histograms that consecutive
   codes go to in turn, merged into `h` at the end.
3. Run `bench_spectrum` (release, pinned) for uniform codes, a 511 keV photopeak and a
   constant code. Explain the numbers: what limits the simple version when the same bin comes
   up again and again, why the split version helps exactly then, and why a realistic
   photopeak is closer to the uniform case than to the constant one.

**Acceptance tests** (`tests/test_spectrum.cpp`): both versions equal a reference for sizes
that are and are not multiples of 4, codes above 11 bits are masked, results accumulate across
calls, and a bin that passes 2^32 does not wrap.
