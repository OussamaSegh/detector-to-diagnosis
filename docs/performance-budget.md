# MiniDAQ performance budget

Status: measured on the book's machine at tag `ch05`, with a realistic-stream section from tag `ch11` and the list-mode writer from tag `ch12`. Every number must be re-measured on the
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

## The pipeline with a realistic stream (Chapter 11)

The table above uses synthetic words. Chapter 11 replays the simulator's NEMA-style stream
(no dead time; about 63% of the singles outside the 435 to 585 keV window) through the whole
pipeline in real time with `minidaq_latency --words` and reads each stage's busy share of the
wall time (`measurements/ch11/bottleneck.txt`, same machine, `release` preset, two runs of
3 s per rate):

| Stage | Busy at 16.7 M singles/s | Busy at 66.8 M singles/s | Fitted capacity |
|---|---|---|---|
| Decode | 6.7 to 6.8% | 19.0 to 19.8% | about 330 M singles/s |
| Sort | 19.1 to 19.6% | 68.1 to 69.0% | about 96 M singles/s |
| Pair (coincidence sorter) | 22.9 to 23.0% | 97.3 to 97.5% | about 70 M singles/s |

The pair stage is the binding stage with realistic data: at 66.8 M singles/s it is 97% busy
and the source drops 0.06 to 0.17% of the words. Its margin is about 7x at the 10 M singles/s
working rate and 2.3x at 30 M singles/s. The replay source's own busy time (about 65% at
high rates) is clock reads and copies, not a limit of the pipeline.

## The list-mode writer and the disk (Chapter 12)

The writer's load is coincidences, not singles: at the pair stage's limit of 70 M singles/s
the sorter produces about 2.7 M coincidences/s (0.039 per single, `bm_sorter`), 43 MB/s of
16-byte records. Same machine, `release` preset; raw results in `measurements/ch12/`.

| Item | Measured | Margin against 2.7 M coincidences/s | Source |
|---|---|---|---|
| Encode one record, both CRCs | 20 ns (49.3 M records/s) | 18x | `bm_listmode` `BM_EncodeBlocks` |
| CRC-32, slicing-by-8 | 2.07 GiB/s (7 ns per record) | | `bm_listmode` `BM_Crc32Slicing8` |
| Read, check and decode | 80.9 M records/s | 30x | `bm_listmode` `BM_ReadBlocks` |
| Histogram into SSRB sinograms | 37.0 M coincidences/s | 14x | `bm_listmode` `BM_Histogram` |
| Sink on the disk, fsync `close`, 3.2 GB | 19.0 M coincidences/s (about 300 MB/s) | 7.0x | `writer_throughput`, `writer.txt` |
| Sink on the disk, fsync every 256 blocks, 3.2 GB | 18.6 M coincidences/s | 6.9x | `writer_throughput`, `writer.txt` |
| Sink on the disk, fsync every 16 blocks, 3.2 GB | 20.5 M coincidences/s | 7.6x | `writer_throughput`, `writer.txt` |

Short runs (320 MB) reach 23 to 38 M coincidences/s because the page cache absorbs them; only
runs longer than the kernel's dirty limit (20% of 15 GiB here) measure the disk. The VM's disk
is a virtual disk that the host may cache (a repeated 3 GB `dd` ran at 1.4 GB/s against
278 MB/s the first time): re-measure on the acquisition PC's disk before relying on the margin
(verify on the acquisition PC).

## Regression gate

The rows with a library benchmark (`bm_*`) are gated by `.github/workflows/perf.yml`: `tools/perf_suite.sh`
runs them with 10 repetitions and `tools/perf_gate.py` fails the merge request if one is more
than 5% slower than `benchmarks/baseline/<runner>.json` with p < 0.01 (one-sided Mann-Whitney U).
A change that intentionally slows a row updates the baseline and this table in the same merge
request, with a reason.
