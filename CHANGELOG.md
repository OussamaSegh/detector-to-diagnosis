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
