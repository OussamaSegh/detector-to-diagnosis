# Notes on the solution

`alignas(64)` on `Counters` gives each stage's block its own line. Measured with
`build/release/benchmarks/bm_false_sharing` (4 vCPU Xeon @ 2.30 GHz VM, GCC 13.3, -O2):
two threads each doing one million relaxed `fetch_add`s on their own counter took 36.1 ms
when the counters shared a line and 5.9 ms when padded: a 6x slowdown caused purely by the
line bouncing between the two cores' caches, with no logical sharing at all.

How to spot it in a profile: the hot instruction is a `lock add` (or a plain store) that
takes far more cycles than it should, and on bare metal `perf c2c` (cache-to-cache) reports
the line as heavily contended, with "HITM" (hit-modified) loads from two CPUs on different
offsets of the same line. Code review catches it earlier: any array or struct of per-thread
mutable data is suspect.

Cost of the fix: 64 bytes per stage instead of 24, irrelevant here. Do not pad everything
blindly: per-event structs must stay small (Chapter 2's 16-byte `Single`); padding is for
per-thread or per-core state.

Why not `std::hardware_destructive_interference_size`? See `minidaq/core/cache.hpp`: GCC
warns when it is used in headers (ABI hazard across -mtune settings) and Clang with libstdc++
does not provide it before Clang 19.
