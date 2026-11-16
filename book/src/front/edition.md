```{=latex}
\frontmatter
```

# About this edition {.unnumbered}

This is the **Second Edition**, **version {{version}}** ({{date}}), of *Detector to Diagnosis*.
The first edition was released Part by Part, each Part bumping the minor version, and version
1.0.0 was the complete, packaged book. The Second Edition, version 2.0.0, adds Part X and
moves MiniDAQ to interfaces that break compatibility with the first edition's. The version of
this file is printed on the title page and in every output file name.

| Part | Chapters | Version | Status |
|--------------------------|-----------|------|------|
| I. Modern, low-latency C++ | 1 to 7 | 0.1.0 | complete |
| II. PET physics and data acquisition | 8 to 12 | 0.2.0 | complete |
| III. Medical device software standards | 13 to 17 | 0.3.0 | complete |
| IV. Testing, verification and quality | 18 to 21 | 0.4.0 | complete |
| V. Hardware, embedded Linux and networking | 22 to 25 | 0.5.0 | complete |
| VI. Calibration, corrections and reconstruction | 26 to 30 | 0.6.0 | complete |
| VII. Python and tooling | 31 to 32 | 0.7.0 | complete |
| VIII. Capstone | 33 to 34 | 0.8.0 | complete |
| IX. Imaging IT, team workflow and AI-assisted coding | 35 to 37 | 0.9.0 | complete |
| Appendix A. Software architecture and design | | 0.9.0 | complete |
| The first edition, complete and packaged | 1 to 37, Appendix A | 1.0.0 | complete |
| X. Time, flight and the years after release | 38 to 40 | 2.0.0 | complete |
| The Second Edition | 1 to 40, Appendix A | 2.0.0 | complete |

**For readers of the first edition.** What changed between 1.0.0 and 2.0.0, in the order of the
releases (the CHANGELOG of the companion repository lists every change):

- **1.1.0** gave the book a new interior: page design, figures and the thumb tabs.
- **1.2.0** checked every listing, figure and cross-reference with new tools, and added the web
  edition, one page per chapter.
- **1.3.0** added time markers to the front-end boards' data (register map 1.2) and signed run
  records, calibration tables and reports.
- **2.0.0** is the breaking release. C++23 is the baseline (GCC 13, Clang 18): with GCC,
  `minidaq::Expected` is now `std::expected` itself, and the first edition's shim remains only for
  Clang 18, whose standard library hides `std::expected`. The shipped server is built without the
  simulator and refuses simulated data. The control API moves to major version 3 and the
  acquisition configuration to schema 2 (3.1 and 2.1 at this release), with renamed fields: a 1.x
  configuration or a 2.x request is refused with a message that names `docs/migration-2.0.md`,
  and `tools/migrate_config.py` converts a configuration. Every listing, exercise and solution uses the new interfaces. Part X adds
  Chapter 38, on clock distribution and a monitor of the scanner's time base, Chapter 39, time of
  flight in the reconstruction, and Chapter 40, the maintenance of a released product, with
  MiniDAQ's own history from 1.0 to 2.0 as its example.

The companion repository (`minidaq-vX.Y.Z.zip`) contains MiniDAQ with one git tag per
chapter (`ch00` is the empty starting point, then `ch01`, `ch02` and so on, to `ch40`),
every exercise starter and solution, the Python analysis package, and the complete
regulatory file with the release records of every version. Every code listing in this book is
included from that repository at build time, so every listing is compiled and tested.

Hardware numbers in this book are typical values for a brain PET scanner and are marked
*assumption: confirm with team*. The copyright page says what the book is not a substitute
for.
