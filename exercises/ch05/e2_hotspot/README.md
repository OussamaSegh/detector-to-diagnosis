# Exercise 5.2 (M): Find the hotspot with a flame graph, and fix it

**Goal.** `ex::EventSource` produces a realistic-looking stream of singles (Poisson arrivals,
uniform crystals, energies around 511 keV, 30% of primaries with a partner on the opposite
side of the ring). It is correct, and it is slow: about 50 ns per single on the book's
machine, which is more than the whole pipeline spends on a single after Chapter 5's sort fix.
Profile it, find where the time goes, and make it at least three times faster without changing
what it produces statistically.

**Time.** 2 to 3 hours.

**Tasks.**
1. Build the `profile` preset with starters (`cmake --preset profile
   -DMINIDAQ_BUILD_STARTERS=ON && cmake --build --preset profile`) and record a flame graph of
   the benchmark: `tools/flamegraph.sh source.svg
   build/profile/exercises/ch05/ch05_e2_hotspot_starter_bench --benchmark_min_time=3s`. Open
   the SVG in a browser and write down the three widest frames under `generate`.
2. Fix them in `event_source.hpp/.cpp`, one at a time, re-measuring after each change with
   `ch05_e2_hotspot_starter_bench` (pinned with `taskset`, 5 repetitions). Keep a table of
   what each change bought.
3. The interface stays the same. The output does not need to be bit-identical to the starter's,
   but the same seed must still give the same stream.

**Acceptance tests** (`tests/test_event_source.cpp`): time order and determinism; primary rate
within 1%; pair fraction within 0.005; energy mean and standard deviation within 0.2 keV and
the fractions within 1 and 2 sigma within 0.3%; uniform crystals; and, in release builds
without sanitizers, a third of the time per single of the starter's algorithm, which the test
times on the same machine in the same run (`EX_NS_PER_SINGLE` sets a fixed budget in ns
instead; see the test).

**Think about it:** which of your changes would also be acceptable in the *detector
simulator* of Chapter 8, where the energy spectrum's tails matter, and which only in a test
source?
