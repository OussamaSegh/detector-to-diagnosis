# Chapter 2: memory benchmarks

The tables of Chapter 2 were measured when the chapter was written (tag `ch02`, 2026-10-24) and
those first runs were not kept. This directory holds a rerun of the same benchmarks, built from
tag `ch02` with the release preset, on the same kind of machine: a 4 vCPU cloud VM on an Intel
Xeon (reported at 2.1 GHz), GCC 13.3, `-O2`, three repetitions, 2026-11-10.

```bash
git worktree add /tmp/ch02 ch02 && cd /tmp/ch02
cmake --preset release && cmake --build build/release --target bm_latency bm_layout bm_alloc bm_decode bm_false_sharing
measurements/ch02/run.sh /tmp/ch02/build/release      # from the main tree; writes bm_*.json here
```

Book value against the rerun (mean of three repetitions):

| Quantity | Book | Rerun |
|---|---|---|
| Load latency, 16 KiB / 512 KiB / 8 MiB / 64 MiB / 1 GiB | 1.7 / 5.9 / 36 / 138 / 204 ns | 1.6 / 5.7 / 36 / 127 / 161 ns |
| Sum energies AoS, 64 Ki / 100 M singles | 45 µs / 198 ms | 44 µs / 196 ms |
| Sum energies SoA, 64 Ki / 100 M singles | 44 µs / 84 ms | 43 µs / 85 ms |
| Gate on all fields, AoS / SoA, 100 M | 277 / 161 ms | 286 / 154 ms |
| Filter batches: heap / monotonic / reused | 1.84 / 1.62 / 1.66 ms | 1.76 / 1.53 / 1.60 ms |
| Decode 64 Ki / 4 Mi words | 0.20 / 16.0 ms | 0.20 / 13.7 ms |
| Counters, same line, 1 / 2 threads | 6.2 / 36.1 ms | 5.9 / 28.3 ms |
| Counters, padded, 1 / 2 threads | 5.9 / 5.9 ms | 5.9 / 5.9 ms |

Every conclusion the chapter draws holds in the rerun: the latency ladder, SoA 2.3 times faster
from DRAM, the arena about 12% faster than a new vector per batch, and false sharing several
times slower (4.8 here, six in the book). The far-L3 and DRAM latencies and the false-sharing
penalty move most between runs on a VM: they depend on where the hypervisor places the memory
and the two vCPUs.
