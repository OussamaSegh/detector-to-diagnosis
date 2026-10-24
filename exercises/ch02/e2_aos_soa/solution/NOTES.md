# Notes on the solution

Measured on the author's machine (4 vCPU Intel Xeon @ 2.30 GHz cloud VM, GCC 13.3, -O2,
Google Benchmark 1.9.1, mean of 3 repetitions; `build/release/benchmarks/bm_layout`):

| Benchmark (100 M singles) | Time | Throughput | Bytes read per event |
|---|---|---|---|
| Sum energies, AoS | 198 ms | 508 M singles/s | 16 |
| Sum energies, SoA | 84 ms | 1,193 M singles/s | 4 |
| Gate on all fields, AoS | 277 ms | 362 M singles/s | 16 |
| Gate on all fields, SoA | 161 ms | 625 M singles/s | 16 (three arrays) |

With 65,536 singles (1 MiB, fits in L2) both layouts take about 45 microseconds: the loop is
then limited by the chain of dependent floating-point additions, not by memory.

Interpretation:
- From DRAM, the AoS loop drags 16 bytes per event through the memory system to use 4.
  SoA reads only the energy array. The 2.3x gap is less than the 4x byte ratio because at
  1.2 G singles/s the SoA loop starts to be limited by the serial `double` additions.
- `perf stat` on bare metal shows the same story as cache-miss counts: roughly 4x more
  last-level-cache misses for AoS. In the author's VM, hardware counters were not exposed
  (`<not supported>`), so these counts are not reported here.
- The all-fields gate touches every byte in both layouts, yet SoA was still faster. My
  first guess was SIMD, but `g++ -O2 -fopt-info-vec-optimized` reports that *neither* loop
  was vectorized (the short-circuit `&&` and the mix of 32- and 64-bit fields defeat GCC's
  -O2 cost model). Without hardware counters in the VM the remaining gap could not be
  attributed; on bare metal compare `instructions`, `branch-misses` and `L1-dcache-loads`
  for the two loops with `perf stat`. Exercise 5.1 returns to this loop with branchless and
  SIMD variants. The lesson: check a performance explanation with a tool before you write
  it down.
- Converting a stream to SoA costs one pass. It pays off when several passes read a
  subset of fields (histogramming energy, then timing), and not for a one-shot stage
  that needs every field once.
