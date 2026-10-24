# MiniDAQ performance budget

Status: measured on the book's machine at tag `ch05`. Every number must be re-measured on the
acquisition PC before it is used for a design decision (verify on the acquisition PC).

## Requirement and assumptions

- Working rate: 10 M singles/s, the rate MiniDAQ's tools use (assumption: confirm with team).
- High-activity rate: 30 M singles/s, from Chapter 2's stream budget (assumption: confirm with
  team).
- Each pipeline stage runs on its own core, so a stage's budget per single is
  1 / rate: **100 ns** at 10 M singles/s and **33 ns** at 30 M singles/s.
- Margin = budget / measured cost. Below 2x is a design discussion; below 1x the stage cannot
  keep up.

## Machine

4-vCPU Intel Xeon at 2.30 GHz (Firecracker VM, AVX2 and AVX-512), Linux 6.18, GCC 13.3, `-O2`,
`release` preset, single-threaded benchmarks pinned with `taskset -c 2`, medians of 5 or more
repetitions. Raw results: `measurements/ch05/`.

## Budget

| Stage | Work per single | Measured cost, ns per single | Margin at 10 M/s | Margin at 30 M/s | Benchmark |
|---|---|---|---|---|---|
| Receive (source) | Read packed words from the network | not yet measured (built in Chapter 9, tuned in Chapter 23) | | | |
| Decode | Unpack an 8-byte word, unwrap time, check crystal | 3.0 (330 M words/s) | 33x | 11x | `bm_decode` `BM_DecodePacked/65536` |
| Energy window | Branchless filter, 16-byte singles | 1.1 (900 M/s) | 90x | 30x | `bm_energy_filter` `BM_EnergyFilter/1/50/0/4096` |
| Sort | `std::sort` of a 4,096-single batch, inlined comparator | 7.4 to 8.5 (117 to 136 M/s) | 12x | 4x | `bm_sort` `BM_SortFunctor/4096/0` |
| Pair | Coincidence search in sorted singles | not measured separately (gap) | | | `bm_pipeline` only |
| Energy spectrum | `++h[code]`, four sub-histograms | 0.44 (2.26 G/s); 0.81 for a constant code | over 100x | over 40x | Exercise 5.4 `bench_spectrum` |
| Latency histogram | One `record()` per batch | 3 ns per batch (under 0.001 ns per single) | | | `bm_histogram` `BM_HistogramRecord` |
| Whole pipeline | All five stages, 5 threads on 4 vCPUs, batch 4,096 | 11.6 (86 M words/s) | 8.6x | 2.9x | `bm_pipeline` `BM_Pipeline/4096/64/real_time` |

## Hardened builds (Chapter 7)

Shipped builds use the `hardened` preset (ADR 0008). Measured against a build with every
protection off, on the same machine, medians of 5 interleaved runs: decode, energy filter,
histogram and the whole pipeline show no difference outside the VM's noise; the sort is 8 to
18% slower (36 µs per batch of 4,096, 8.8 ns per single, margin 11x at 10 M/s and 3.8x at
30 M/s), caused by `_GLIBCXX_ASSERTIONS`. Raw results: `measurements/ch07/`. The numbers in
the table above are from the `release` preset at tag `ch05`.

## Reading the table

- The whole pipeline is the binding row: at the high-activity rate its margin is under 3x on
  this machine, and the five threads share four vCPUs. On the acquisition PC, with one core per
  stage, re-measure before relying on it.
- The sort is the most expensive single stage. Its cost per single grows with the batch size
  (O(n log n)); a larger batch trades sort cost for fewer hand-offs.
- Pair has no benchmark of its own. Until it does, a regression in it shows up only in the
  pipeline row. Open item: add `bm_pair`.
- The receive stage is the one most likely to be the real bottleneck (system calls, packet
  handling, NIC interrupts) and the one not yet measured.

## Regression gate

The rows with a library benchmark (`bm_*`) are gated by `.github/workflows/perf.yml`: `tools/perf_suite.sh`
runs them with 10 repetitions and `tools/perf_gate.py` fails the merge request if one is more
than 5% slower than `benchmarks/baseline/<runner>.json` with p < 0.01 (one-sided Mann-Whitney U).
A change that intentionally slows a row updates the baseline and this table in the same merge
request, with a reason.
