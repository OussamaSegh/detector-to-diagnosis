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

### Changed
- Release presets use `-O2` explicitly (CMake's default Release is `-O3`).
- Exercise starters build with warnings but without `-Werror` (`minidaq::warnings_no_error`).

### Fixed
- Removed `-Wnull-dereference`: GCC 13 reports false positives inside libstdc++ at `-O2`.
- Exercise test labels: only the variant (`starter`/`solution`) is used as a CTest label.
- EPUB: Graphviz DOCTYPE stripped and SVG files renamed from `.svgz` so epubcheck passes.
