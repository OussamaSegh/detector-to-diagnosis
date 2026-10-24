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
- Chapter 5: energy window filter `minidaq::filter_energy` with branchy, branchless, AVX2 and
  AVX-512 kernels, run-time SIMD dispatch (`simd_kernel`) and the branchless kernel as the
  measured default (`best_kernel`); `TimeOrder`
  function object; benchmarks `bm_energy_filter` and `bm_sort`; `profile` preset (frame
  pointers); tools `flamegraph.sh`, `perf_suite.sh` and `perf_gate.py` (5% threshold with an
  exact Mann-Whitney test); `perf` workflow for a self-hosted runner and the baseline
  `benchmarks/baseline/book-vm.json`; `docs/performance-budget.md`; compiler-flag experiment
  (`measurements/ch05/flags/`); exercises 5.1 to 5.5 (5.3 in Python, run by CTest).
- Chapter 6: library `minidaq_control` with the configuration model and validating reader
  (all errors with JSON Pointer paths, unknown keys with suggestions, `schema_version` rules),
  the table-driven acquisition state machine (ordered listener calls without holding the state
  lock), ports (`DetectorPort`, `CoincidenceSinkPort`, `AuditSink`) and adapters (simulated
  detector, counting sink, JSON Lines audit log), `AcquisitionService` with a monitor thread,
  and the control protocol 1.0 (newline-delimited JSON over TCP, `LineFramer`, `poll` server);
  applications `minidaq_server` and `minidaq_ctl`; configurations `default.json` and
  `short-run.json`; `histogram_interval.hpp` and `recent_latency_ns` in status; the run faults
  on out-of-order singles; nlohmann/json 3.11.3 (control plane only); `docs/architecture/`
  (architecture description v1, diagrams, state table, configuration JSON Schema, layer rules)
  and ADRs 0001 to 0007; `tools/check_layers.py` as the test `architecture.layers`; preset
  `gcc-cxx23` (C++23, `std::expected`) in `ci/run_all.sh` and CI; exercises 6.1 to 6.5 (6.1
  and 6.3 in Python).
- Chapter 7: curated `.clang-tidy`, `tools/cppcheck-suppressions.txt` and
  `tools/static_analysis.sh` (library and applications at zero findings);
  `minidaq/core/parse_number.hpp` (strict number parsing); libFuzzer targets for the decoder,
  raw16, configuration and control protocol with seed corpora, CTest smoke runs (label
  `fuzz`) and the `fuzz` preset; `cmake/Hardening.cmake`, the `hardened` preset,
  `tools/check_hardening.py` as the test `build.hardening`, ADR 0008 and measurements under
  `measurements/ch07/`; `tools/make_sbom.py` (CycloneDX 1.5, reproducible) with vendored
  schemas and the test `tools.sbom`; `docs/regulatory/soup-list.md`; `docs/coding-standard.md`;
  CI jobs `static-analysis`, `fuzz-smoke` and `sbom`, the `hardened` preset in the matrix and
  in `ci/run_all.sh`, and a CodeQL workflow; `JsonLinesAuditLog::failed_writes()`;
  exercises 7.1 to 7.5 (7.3 in Python).
- Chapter 2 (Part I review): worked example on the layout of per-stage counters, and
  common-mistakes boxes for allocation and false sharing.
- Code listings can include Graphviz files from the repository (`{.dot include=...}`).
- Book build fails when a code block's attributes are not parsed (they would otherwise
  render as raw text).

### Changed
- `tsan` preset builds at `-O0`: with Clang 18 at `-O1` and above, TSan did not instrument
  loads from a stack object and missed a seeded race (documented in Chapter 3).
- `to="=}"` in listing includes matches the closing line at the indentation of the `from`
  line, not the first inner brace.
- Release presets use `-O2` explicitly (CMake's default Release is `-O3`).
- Exercise starters build with warnings but without `-Werror` (`minidaq::warnings_no_error`).
- Pipeline stage loops no longer assign inside `if` conditions; `std::stop_token` and
  `PipelineConfig` are passed by `const&`; classes that delete copying also delete moving.
- The `fuzz` preset builds the exercises too (for Exercise 7.2's fuzz target).
- PDF: long inline code may break after `_`, `/`, `.`, `,`, `(` and `::`
  (`book/filters/breakable-code.lua`); Part I no longer has lines in the margin.

### Fixed
- `parse_config` terminated the program on a number too large for a `double` (`6e688`):
  nlohmann/json reports it as `out_of_range`, and only `parse_error` was caught. Found by the
  configuration fuzzer.
- The `rt_profile` path from a control client was read with `std::ifstream`: `/dev/zero` read
  until memory ran out and a FIFO blocked the control thread. It is now opened first and
  checked through the descriptor (regular file, at most 64 KiB).
- Command-line numbers were parsed with `atoi`/`atof`/`atol` in all four programs:
  `--port 70000` listened on port 4464 and `--port abc` on a random port. They are now parsed
  strictly and range-checked.
- The audit trail ignored `fwrite`/`fflush` failures, so a full disk lost records silently;
  failures are counted and `minidaq_server` exits with status 1 if any record was lost.
- `minidaq_ctl` terminated on a response without a `status` object; it now reads with a JSON
  Pointer, rejects responses that are not objects, and catches exceptions in `main`.
- `ControlServer::start` did not check `eventfd` and `getsockname`.
- `LatencyHistogram` accepted any `sub_bucket_bits`; values of 64 or more made a shift
  undefined. It is clamped to 1 to 20.
- Sort stage passed `time_order` as a function pointer, which GCC at `-O2` did not inline: the
  sort stage is 3 times and the pipeline at batches of 4,096 2.5 times faster with `TimeOrder{}`.
- End-to-end latency was measured from when the source read a batch's first word, which hid
  the source's own stalls (coordinated omission); it is now measured from the due time when the
  source provides one, and `minidaq_latency` reports the backlog next to drops.
- cyclictest baseline in Chapter 4: `--policy=other -p0` runs at `SCHED_FIFO` 2; the normal-policy
  runs were repeated with `--policy=other` and no `-p`.
- Chapter 2 overstated the cost of a page fault ("several microseconds"); measured 1.5 µs.
- Listing of `EnergyWindowStage` in the Chapter 2 solutions stopped at an inner `};`.
- Exercise 2.3 allocation test is skipped under TSan as well as ASan (both replace `operator new`).
- Removed `-Wnull-dereference`: GCC 13 reports false positives inside libstdc++ at `-O2`.
- Chapter 4 promised "an asynchronous log" for the pipeline in Chapter 6; the text now
  describes what Chapter 6 does (stages count, a monitor thread reports).
- Chapter 3 called 10 M singles/s "a peak scanner rate"; it is the working rate, and the
  pipeline's 33 M words/s is barely above Chapter 2's high-activity estimate of 30 M singles/s.
  Its decode rate (230 to 260 M words/s) is now marked as a different setup from Chapter 5's
  benchmark (330).
- `minidaq_ctl --help` printed a connection error instead of the usage.
- Exercise test labels: only the variant (`starter`/`solution`) is used as a CTest label.
- EPUB: Graphviz DOCTYPE stripped and SVG files renamed from `.svgz` so epubcheck passes.
