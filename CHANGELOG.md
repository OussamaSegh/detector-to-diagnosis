# Changelog

All notable changes to the book and to MiniDAQ are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/): each completed Part bumps the minor version
(Part I = 0.1.0 ... Part VIII = 0.8.0, packaged release = 1.0.0); fixes after review bump
the patch version.

## [Unreleased]

### Added
- Chapter 1: core types (`Quantity`, `Picoseconds`, `KeV`, `CrystalId`, `Single`,
  `Coincidence`), `minidaq::Expected`, constexpr geometry, raw16 parser; exercises 1.1 to 1.6;
  CMake presets, sanitizer builds, CI workflow; book build pipeline (Pandoc, XeLaTeX, EPUB).
- Chapter 2: MDQ-P1 packed 64-bit single, `TimeUnwrapper`, zero-allocation `StreamDecoder`,
  allocation-counting test binary; Google Benchmark (pinned) and benchmarks `bm_latency`,
  `bm_layout`, `bm_alloc`, `bm_false_sharing`, `bm_decode`; exercises 2.1 to 2.6.
- Chapter 3: `SpscRing`, `MpmcQueue` (Vyukov), `Channel`/`Batch`, `Backoff`, `StageStats`
  (with separate dropped and filtered counts), five-thread `AcquisitionPipeline` with block/drop
  entry policy and drain-on-stop, `SyntheticSource`; memory-model litmus tests; benchmarks
  `bm_spsc` and `bm_pipeline`; exercises 3.1 to 3.6; `tsan` preset in `ci/run_all.sh` and CI.
- Chapter 4: `LatencyHistogram` (log-linear, fixed memory, single writer, `count_at`),
  `monotonic_ns()`, real-time helpers (`minidaq::rt`: pinning, scheduling, timer slack, stack
  prefault, `mlockall`, per-thread page faults, profile files), `PacedSource` with `due_ns` and
  `behind`, pipeline real-time profile applied before `start()` returns, per-stage and
  end-to-end latency histograms, `max_batch_delay`, `due_time_ns`; tools `minidaq_jitter` and
  `minidaq_latency`; profiles `default`, `rt-pin`, `rt-fifo`; benchmark `bm_histogram`;
  exercises 4.1 to 4.6; raw measurements under `measurements/ch04/`.
- Book build fails when a code block's attributes are not parsed (they would otherwise
  render as raw text).

### Changed
- `tsan` preset builds at `-O0`: with Clang 18 at `-O1` and above, TSan did not instrument
  loads from a stack object and missed a seeded race (documented in Chapter 3).
- `to="=}"` in listing includes matches the closing line at the indentation of the `from`
  line, not the first inner brace.
- Release presets use `-O2` explicitly (CMake's default Release is `-O3`).
- Exercise starters build with warnings but without `-Werror` (`minidaq::warnings_no_error`).

### Fixed
- End-to-end latency was measured from when the source read a batch's first word, which hid
  the source's own stalls (coordinated omission); it is now measured from the due time when the
  source provides one, and `minidaq_latency` reports the backlog next to drops.
- cyclictest baseline in Chapter 4: `--policy=other -p0` runs at `SCHED_FIFO` 2; the normal-policy
  runs were repeated with `--policy=other` and no `-p`.
- Chapter 2 overstated the cost of a page fault ("several microseconds"); measured 1.5 µs.
- Listing of `EnergyWindowStage` in the Chapter 2 solutions stopped at an inner `};`.
- Exercise 2.3 allocation test is skipped under TSan as well as ASan (both replace `operator new`).
- Removed `-Wnull-dereference`: GCC 13 reports false positives inside libstdc++ at `-O2`.
- Exercise test labels: only the variant (`starter`/`solution`) is used as a CTest label.
- EPUB: Graphviz DOCTYPE stripped and SVG files renamed from `.svgz` so epubcheck passes.
