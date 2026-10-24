# Exercise 2.2 (M): AoS vs SoA on 100 M events

**Goal.** Implement `to_soa()` and the two energy sums in `layout.hpp`, then run the
benchmark on 100 M singles and explain the difference with numbers: bytes moved per
event, and (on bare metal) `perf stat -e cache-misses,cycles,instructions`.

**Time.** 60 to 90 minutes.

**Acceptance tests.** `tests/test_layout.cpp`: both sums agree with a reference to 1e-9
relative error; `to_soa()` preserves every field. Then:
```bash
cmake --preset release && cmake --build --preset release
build/release/exercises/ch02/ch02_e2_aos_soa_solution_bench --benchmark_repetitions=3
perf stat -e cache-misses,cycles,instructions build/release/exercises/ch02/ch02_e2_aos_soa_solution_bench --benchmark_filter=100000000
```
Hardware counters are not available inside most VMs and containers (`<not supported>`);
run `perf stat` on bare metal or a laptop.
