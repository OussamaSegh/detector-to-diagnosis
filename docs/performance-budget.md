# MiniDAQ performance budget

Version 4 (MiniDAQ 0.4.0-dev, release 0.4.0). Status: measured on the book's machine at tag `ch05`, the whole pipeline again for releases 0.3.0 and 0.4.0, with a realistic-stream section from tag `ch11` and the list-mode writer from tag `ch12`. Every number must be re-measured on the
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
| Pair | The coincidence sorter (Chapter 10) | not measured separately (gap); the pipeline row shows its cost | | | `bm_pipeline` only |
| Energy spectrum | `++h[code]`, four sub-histograms | 0.44 (2.26 G/s); 0.81 for a constant code | over 100x | over 40x | Exercise 5.4 `bench_spectrum` |
| Latency histogram | One `record()` per batch | 3 ns per batch (under 0.001 ns per single) | | | `bm_histogram` `BM_HistogramRecord` |
| Whole pipeline | All five stages, 5 threads on 4 vCPUs, batch 4,096, pair stage = coincidence sorter | 26.4 (37.9 M words/s; 35.4 to 40.4) | 3.8x | 1.3x | `bm_pipeline` `BM_Pipeline/4096/64/real_time` |

The whole-pipeline row was measured for release 0.3.0 (`release` preset, 10 repetitions, commit
`5fa917b`, `measurements/release-0.3.0/perf-current-5fa917b.json`). Until then it showed 11.6 ns (86 M words/s), measured
at tag `ch05` with the pair stage of Chapter 3, which only matched neighbors. Chapter 10 made the
pair stage the coincidence sorter (commit `b4422de`), which does the real work and costs most of
the difference: interleaved runs of the `hardened` build give 96 M words/s just before that
commit, 39 M words/s at it and 39 M words/s at the release (`pipeline-attribution.txt`). The
change was intended; that this row and SRS-PERF-020's evidence kept the old number for seven
chapters was not (MDQ-PR-014, CAPA-0004). This synthetic stream puts every single in the energy
window and is a heavier load for the sorter than Chapter 11's realistic stream, in which about
63% of the singles are filtered out before it.

Release 0.4.0 measured the row again (`hardened` preset, 5 repetitions, commit `6766495`,
`measurements/release-0.4.0/perf-pipeline.txt`): median 36.6 M words/s, 27.3 ns per single, a
margin of 3.7 times at 10 M singles/s. No code of the pipeline's stages changed between the two
releases except the sorter's order of singles with equal times (SRS-SRT-013).

## Hardened builds (Chapter 7)

Shipped builds use the `hardened` preset (ADR 0008). Measured against a build with every
protection off, on the same machine, medians of 5 interleaved runs: decode, energy filter,
histogram and the whole pipeline show no difference outside the VM's noise; the sort is 8 to
18% slower (36 µs per batch of 4,096, 8.8 ns per single, margin 11x at 10 M/s and 3.8x at
30 M/s), caused by `_GLIBCXX_ASSERTIONS`. Raw results: `measurements/ch07/`. The numbers in
the table above are from the `release` preset at tag `ch05`.

## Reading the table

- The whole pipeline is the binding row: at the high-activity rate its margin is 1.3x on this
  machine with the synthetic stream, below the 2x of a design discussion, and the five threads
  share four vCPUs. On the acquisition PC, with one core per
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
| Sink on the disk, fsync `close`, 3.2 GB, release 0.4.0 | 14.0 to 16.4 M coincidences/s (3 runs) | 5.2x | `measurements/release-0.4.0/perf-writer.txt` |

Short runs (320 MB) reach 23 to 38 M coincidences/s because the page cache absorbs them; only
runs longer than the kernel's dirty limit (20% of 15 GiB here) measure the disk. The VM's disk
is a virtual disk that the host may cache (a repeated 3 GB `dd` ran at 1.4 GB/s against
278 MB/s the first time): re-measure on the acquisition PC's disk before relying on the margin
(verify on the acquisition PC).

## Regression gate

The rows with a library benchmark (`bm_*`) are compared with `benchmarks/baseline/<runner>.json`
by `tools/perf_suite.sh` (10 repetitions) and `tools/perf_gate.py`, which fails if one is more
than 5% slower with p < 0.01 (one-sided Mann-Whitney U). Until release 0.3.0 the comparison
was wired only into `.github/workflows/perf.yml`, which needs a self-hosted runner labelled
`perf` that does not exist, so it never ran (MDQ-PR-014). Since then `tools/release_checks.sh`
runs it on the reference machine before every release, and a release record without its output
is incomplete (CAPA-0004). A change that intentionally slows a row updates the baseline and this
table in the same change, with a reason; the `BM_Pipeline` entries were replaced at release
0.3.0 because Chapter 10 made the pair stage the coincidence sorter.

At release 0.4.0 the gate failed, twice on two commits: `BM_EnergyFilter/1` and `/3` ran 18% and
23% slower than the baseline (p < 0.0001, `measurements/release-0.4.0/perf-gate.txt`), while
`BM_DecodePacked` ran 48% faster. No code that the energy-filter benchmarks run changed since
0.3.0. An interleaved A/B on the same machine in one job (`tools/perf_ab.sh`, the release build
of tag `book-v0.3.0` against that of commit `6766495`, 5 rounds of 2 repetitions) found no
regression: speed 1.02 and 1.00 for the two rows, `BM_Pipeline` 0.95 with p = 0.06
(`measurements/release-0.4.0/perf-ab/gate.txt`). The machine is slower than on the day the
baseline was recorded, which a shared VM can be. The baseline is kept: re-recorded on a slow day,
it would let a real regression of the same size pass on a fast one. The release record shows
both results; when the baseline gate and the A/B disagree, the A/B decides whether code got
slower, and the baseline gate says whether the margins of this table still hold.

## Document history

| Version | Change |
|---|---|
| 1 | First controlled version (Chapter 16). Earlier states, without versions, are in git at tags `ch05`, `ch07`, `ch11` and `ch12`. |
| 2 | Release 0.3.0: the whole pipeline re-measured with the coincidence sorter (MDQ-PR-014, CAPA-0004); the regression baseline updated for `BM_Pipeline`. |
| 3 | Editorial: the repository's history was rewritten to remove personal data, so the cited commit hashes are those of the rewritten commits; the content is unchanged. |
| 4 | Release 0.4.0: the whole pipeline and the list-mode writer re-measured; the regression gate's failure explained by an interleaved A/B, and the baseline kept. |
