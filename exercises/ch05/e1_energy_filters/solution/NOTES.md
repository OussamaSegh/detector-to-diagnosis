# Exercise 5.1 notes

**Measured** (book's machine, GCC 13.3 `-O2`, `release`, `taskset -c 2`, 100 M singles, 5
repetitions, median, M singles/s; raw: `measurements/ch05/e1_filters_100M.json`):

| Kernel | Random 10% | Random 50% | Random 90% | Sorted 10% | Sorted 50% | Sorted 90% |
|---|---|---|---|---|---|---|
| branchy | 141 | 158 | 292 | 420 | 370 | 364 |
| branchless | 345 | 337 | 311 | 353 | 331 | 314 |
| SIMD (AVX2) | 338 | 346 | 317 | 340 | 328 | 313 |

`memcpy` of 1,600 MiB on the same machine: 1.40 ns per 16 bytes (714 M singles/s).

**Branchy.** With random energies, `e >= lo && e <= hi` compiles to two branches. The expected
mispredictions per single are about 0.55 at 10% (the first branch is true 55% of the time),
0.50 at 50% and 0.10 at 90%, and the speed follows them, not the number of copies. Sorted, the
branches are predictable and the kernel copies only what passes, so it is the fastest at 10%.

**SIMD.** 2% faster than branchless at 50%, 2% slower at 10%: nothing. The data is 1.6 GB, so
every kernel streams from memory; the AoS layout wastes three of every four float lanes; and
compaction needs shuffles.

**Bandwidth.** Branchless at 50% moves 24 bytes per single by the benchmark's count (16 read,
8 written on average), 7.5 GiB/s, against `memcpy`'s 21 GiB/s. Normal stores also read each
destination line first (read for ownership), and glibc's large `memcpy` avoids that with
non-temporal stores (verify: glibc tunables), which explains most of the gap.

**In cache** (the chapter's `bm_energy_filter`, 4,096 singles per batch) the branchless kernel
is 2.6 times faster (915 M singles/s): the memory, not the instructions, sets the speed here.
