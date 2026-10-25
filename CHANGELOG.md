# Changelog

All notable changes to the book and to MiniDAQ are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/): each completed Part bumps the minor version
(Part I = 0.1.0 ... Part VIII = 0.8.0, packaged release = 1.0.0); fixes after review bump
the patch version.

## [Unreleased]

### Added
- Chapter 13: the regulatory file in `docs/regulatory/` starts with the intended-use
  statement (`intended-use.md`), the regulatory context for the EU, the US and Switzerland
  (`regulatory-context.md`) and the standards map (`standards-map.dot` and `.svg`);
  `tools/check_regulatory.py` and the test `docs.regulatory` keep them complete and their
  links valid; Part III introduction; exercises 13.1 to 13.4 (all in Python: the standards
  map, a change brief, a model of the MDR classification rules, the vigilance clocks).
- Chapter 14: IEC 62304. `docs/regulatory/srs.md` defines all 114 software requirements
  (112 verified by test, 2 by measurement), checked by `tools/req_lint.py` (test `docs.srs`);
  `tools/trace_matrix.py` generates `docs/regulatory/trace-matrix.md` and fails on any gap
  (test `docs.trace`); `docs/architecture/software-items.json` classifies every software item,
  checked by `tools/check_items.py` (test `architecture.items`); architecture description
  version 5 (items, safety classes, segregation); SOUP list version 2 with the known-anomaly
  review of nlohmann/json 3.11.3 against the 3.12.0 release notes, checked against the build's
  pins by `tools/check_soup.py` (test `docs.soup`); problem reports and the generated
  known-anomalies list (`tools/anomalies.py`, test `docs.anomalies`); the software development
  plan `docs/regulatory/sdp.md`; exercises 14.1 to 14.6 (all in Python).
- Chapter 15: ISO 14971. The software part of a risk management file in
  `docs/regulatory/risk/`: the risk management plan, the criteria and nine hazards with
  twenty risk controls (`hazards.json`), an FMEA of the coincidence sorter and a fault tree
  of silent data loss; `tools/check_risk.py` (test `docs.risk`) checks them against the SRS,
  the tests and the software item classification. The acquisition service reports an
  integrity verdict (`assess_integrity`) in its status and in every run record, and records
  the loss counters of an incomplete run in the audit trail. Seven new requirements
  (SRS-CTL-030 to 032, SRS-OUT-011, SRS-OUT-012, SRS-FMT-013, SRS-SRT-012), ten new or newly
  tagged tests, and a risk-control column in the trace matrix; exercises 15.1 to 15.5 (15.2 in
  C++, the others in Python).
- Chapter 16: ISO 13485. The design and development file `docs/regulatory/qms/design-file.json`
  (18 clauses, 13 controlled documents) with `tools/design_file.py` (test `docs.design_file`;
  `--since` the last release tag in `ci/run_all.sh` and the CI job `document-control`); every
  controlled document has a version and a history table. Change control in
  `docs/regulatory/changes/` (procedure, template, CR-0001 to CR-0003) checked by
  `tools/check_changes.py` (test `docs.changes`); CAPA in `docs/regulatory/capa/` (procedure,
  template, CAPA-0001 and CAPA-0002) checked by `tools/check_capa.py` (test `docs.capa`); the
  internal audit report of 2026-10-25 with four nonconformities and two observations;
  `tools/stress_tests.sh`, `minidaq/tests/unit/eventually.hpp`, coding standard rule 5.5 and the
  test `tests.waits`; problem reports MDQ-PR-010 to MDQ-PR-012; exercises 16.1 to 16.5 (all in
  Python).

### Changed
- Control API 1.1 (CR-0003, ADR 0013): the status's top-level fields are listed in
  `status_fields`, and SRS-CTL-033 with `ControlProtocol.StatusFieldsMatchTheApiVersion` keeps the
  list true; `minidaq_ctl` sends 1.1, and 1.0 clients keep working.
- nlohmann/json 3.12.0 (CR-0002), with a new known-anomaly review in the SOUP list; MDQ-PR-005
  closed. Its evaluation rested on a wrong cause, now corrected.
- SDP version 3 states the review that MiniDAQ actually does (CAPA-0002) and adds the stress run,
  change requests, CAPA and document control to the verification table.
- Requirement tags added to `Config.TypesAndRangesAreCheckedAndAllErrorsReported`
  (SRS-CFG-004), `RtProfile.RejectsBadInputWithLineNumbers` (SRS-RT-001) and
  `Realtime.InvalidCpuIsAnError` (SRS-RT-002).

### Fixed
- The sorter's FMEA found that nothing required how `take_winner_of_goods` breaks a tie
  between pairs of equal summed energy; the existing rule (the earlier pair) is now
  SRS-SRT-012 with a test.
- The decoder's invalid words were counted only as "filtered", like singles outside the energy
  window; the integrity verdict counts them as a loss, and SRS-FMT-013 requires the counter.
- `FastSorter.FastEnough` (Exercise 10.4) measured the two sorters in separate blocks, so a
  slow spell of a shared machine could fail it; it now takes the best of seven interleaved runs.
- Seven tests asserted after a fixed sleep or on a throughput that depends on the test's own
  thread (CAPA-0001); under load the ThreadSanitizer build failed two of them. They now wait for
  their condition, and the stress run passes 100 repetitions.

## [0.2.0] - 2026-10-25

Part II, PET physics and data acquisition (Chapters 8 to 12), complete and reviewed.

### Added
- Chapter 8: `minidaq/sim/physics.hpp` (Compton kinematics, Klein-Nishina shape, water
  attenuation from the NIST table, ray geometry); `DetectorSimulator` (Poisson decays in a
  point or cylinder source, non-collinearity, Compton scatter in a water phantom, a crystal
  ring with depth of interaction, photofraction, energy and time blur, threshold,
  time-ordered output with ground truth per single); `count_coincidences`, a reference
  counter by truth; the tool `minidaq_sim`; figure script
  `book/tools/figures/ch08_energy_spectrum.py`; exercises 8.1 to 8.5 (8.1 and 8.2 in
  Python).
- Chapter 9: readout packet format MDQ-R1 (`minidaq/format/readout_packet.hpp`) with a
  field-by-field parser, serial-number arithmetic and `SequenceTracker` (in-order delivery
  within a window and a hold time; every packet delivered, lost, stale or rejected; resync on
  a source restart); `sim::Packetizer` and `sim::LinkFaults` (reproducible loss, reordering,
  duplication); `control::UdpDetector` (non-blocking `recvmmsg`, reports the receive buffer
  the kernel granted); `DetectorPort::counters()` and `detector_counters` in the status
  report; configuration schema 1.1 with `source.type` `"udp"`; the tool `minidaq_send`; the
  configuration `udp-loopback.json`; fuzz target `fuzz_packet`; loopback measurements
  (`measurements/ch09/`); ADR 0009; figure script `ch09_time_walk.py`; exercises 9.1 to 9.5
  (9.4 and 9.5 in Python).
- Chapter 10: `processing::CoincidenceSorter` (fixed or per-single windows; kill all, take
  all goods, take the winner of goods and keep if only one good; energy, sector and
  field-of-view gates; a delayed window; eleven counters with an accounting identity; the
  same output for any chunking) and `processing::StreamMerger` (k-way heap merge released by
  a watermark, time markers, `max_skew`, late and out-of-order counters, deterministic
  ties); configuration schema 1.2 with a `sorter` section; the sorter's counters in the
  status report; `minidaq_sim` options `--mode`, `--policy`, `--delay`, `--sectors`, `--fov`
  and a report classified by truth; validation against truth from 1 to 40 MBq
  (`measurements/ch10/validation.txt`); benchmark `bm_sorter`; fuzz target `fuzz_sorter`;
  ADR 0010; figure scripts `ch10_windows.py` and `ch10_policies.py`; exercises 10.1 to 10.6
  (10.6 in Python).
- Chapter 11: `sim::DeadTime` (non-paralyzable or paralyzable dead time per block or per
  crystal, optional pile-up, events released in time order, the same output for any
  chunking) with the analytical `recorded_rate` and `true_rate`; `CountRates` (prompts,
  scatter fraction, NECR for a given k); `sim::ReplaySource` (a recorded stream looped in
  time order at a chosen rate); `minidaq_sim` options `--deadtime`, `--tau`, `--pileup`,
  `--deadtime-unit`, `--nema` and a `countrate` line; `minidaq_latency` options `--words` and
  `--speed` and a per-stage utilization table; measurements `countrate`, `windows`,
  `frontend` and `bottleneck` (`measurements/ch11/`); ADR 0011; figure scripts
  `ch11_deadtime.py`, `ch11_countrate.py` and `ch11_windows.py`; exercises 11.1 to 11.5
  (11.3 to 11.5 in Python).
- Chapter 12: CRC-32 (`minidaq/core/crc32.hpp`, slicing-by-8 with a bytewise reference) and
  shared little-endian loads and stores (`minidaq/core/byte_io.hpp`); the list-mode format
  MDQ-L1 (`minidaq/format/list_mode.hpp`: versioned header with JSON metadata, blocks of
  16-byte records with header and payload CRCs, tags, `BlockWriter`, a resynchronizing
  `Reader`) and its specification `docs/formats/mdq-l1.md`; `processing::Histogrammer`
  (`lor_bin`, uneven radial positions, SSRB, TOF bins, delayeds apart, Michelogram,
  Interfile-style header); `control::FileOps` and `control::ListModeSink` (encoding on the
  writer thread, an I/O thread, a buffer pool with backpressure, rotation, fsync policies
  `none`, `close` and `interval`, `.part` files renamed without replace, faults, a run
  record `<prefix>-<run>.run.json` with the service's final status); configuration schema
  1.3 with an `output` section; `sink_counters` in the status report; the tool
  `minidaq_listmode` (`info`, `verify`, `sino`); `minidaq_sim` options `--centre`,
  `--listmode`, `--max-file-mb` and `--fsync`; benchmarks `bm_listmode` and
  `writer_throughput`; fuzz target `fuzz_listmode` and a corpus written by an independent
  Python implementation; measurements `writer`, `crash`, `sinogram` and `bm_listmode`
  (`measurements/ch12/`); ADR 0012; figure scripts `ch12_sinogram.py` and `ch12_writer.py`;
  exercises 12.1 to 12.5 (12.2, 12.4 and 12.5 in Python).

### Changed
- `CoincidenceSinkPort` gains `close(run_record)` and `counters()`; the service closes the sink
  when the stages have drained, and a sink that cannot make the run durable ends it in a fault.
- ADR 0007 (list-mode file format, proposed) is superseded by ADR 0012.
- The architecture description, the component diagram and the performance budget describe
  the list-mode writer.
- The pipeline's pair stage is the coincidence sorter instead of a placeholder that paired
  consecutive singles. Configuration files of schema 1.0 and 1.1 remain valid but now get the
  sorter's defaults: a 435 to 585 keV energy gate, a delayed window at 100 ns, kill all and a
  minimum sector difference of 1. Coincidence counts from earlier versions are not
  comparable.
- `PipelineConfig::coincidence_window` is replaced by `PipelineConfig::sorter`.
- Solutions manual: chapter titles no longer repeat "Chapter N:" before the chapter number
  the layout already prints.
- CI uses `actions/checkout@v5` (Node.js 20 is deprecated on GitHub's runners).
- The configuration schema test walks nested objects of the JSON Schema document.
- Chapter 6's component diagram is frozen in the book (`book/src/diagrams/`); the live
  diagram in `docs/architecture/` now shows the UDP readout.

### Fixed
- `minidaq_latency` let an exception escape `main` and failed `clang-tidy`
  (`bugprone-exception-escape`, `modernize-use-auto`); exceptions are now caught and
  reported.
- `test_replay_source.cpp` reused the requirement IDs SRS-SIM-010 and 011 of the physics
  tests; the replay source's requirements are SRS-SIM-020 and 021.
- `clang-tidy` in CI failed on every file: newer CMake versions scan C++20 sources for
  modules and write `@modmap` arguments into `compile_commands.json`.
  `CMAKE_CXX_SCAN_FOR_MODULES` is off (MiniDAQ uses no modules).
- `Pipeline.DropPolicyCountsEveryLostWord` depended on a slow sink being slower than the
  source, which a fast GitHub runner broke in the debug build; the sink now stalls until
  the source has read everything.
- `PacedSource.NeverDeliversAheadOfTheClock` failed in the ThreadSanitizer build on a
  GitHub runner, which could not generate 1 M words/s under instrumentation; the test now
  paces at 200 k words/s and checks the same two bounds.
- Exercise 9.3 built `std::normal_distribution` with a standard deviation of zero for an
  ideal clock, which the standard does not allow; the hardened build's library assertions
  caught it. Zero jitter now draws nothing.
- `AcquisitionService::start` created the new run's detector before releasing the previous
  one, so a second run on the same UDP port failed with "address already in use"; the
  previous run's pipeline and ports are now released first.
- Configuration validation of the detector simulator accepted NaN in several fields.
- Coincidence sorter (found before release): per-single windows with take all goods emitted
  a pair twice, once from each opener's window; a per-single window now pairs its opener
  only. The delayed window's winner of goods now compares summed energy, as the prompt
  window does.
- `clang-tidy` asked for the energy gate in De Morgan form, which would let NaN energies
  through; the NaN-safe form stays, with a documented suppression.
- A 0.6 pt overfull table in the Chapter 5 solutions.
- Part II review: wrong cross-references in Chapters 10 to 12 (randoms correction is
  Chapter 27, the crystal position table Chapter 1, the latency histogram Chapter 4, the
  stated assumptions Chapter 5's performance budget); Chapter 10 explains why the sorter's
  energy window is narrower than Chapter 8's counter.
- Six test files used `std::find`, `std::min`, `std::equal` or `std::fill` without
  `<algorithm>`, which broke the Clang builds on GitHub's runners.
- The README promised a `python/` package that arrives in later Parts; it now lists the
  measurements directory and the command-line tools.

## [0.1.0] - 2026-10-24

Part I, Modern, low-latency C++ (Chapters 1 to 7), complete and reviewed.

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
