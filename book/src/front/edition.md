```{=latex}
\frontmatter
```

# About this edition {.unnumbered}

This is **version {{version}}** ({{date}}) of *Detector to Diagnosis*. The book was released
Part by Part, each Part bumping the minor version; version 1.0.0 is the complete, packaged
book, with every Part, the appendix and the companion repository verified together. The
version of this file is printed on the title page and in every output file name.

| Part | Chapters | Version | Status |
|---|---|---|---|
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
| The complete, packaged book | 1 to 37, Appendix A | 1.0.0 | complete |

The companion repository (`minidaq-vX.Y.Z.zip`) contains MiniDAQ with one git tag per
chapter (`ch00` is the empty starting point, then `ch01`, `ch02` and so on, to `ch37`),
every exercise starter and solution, the Python analysis package, and the complete
regulatory file with the release records of every version. Every code listing in this book is
included from that repository at build time, so every listing is compiled and tested.

Hardware numbers in this book are typical values for a brain PET scanner and are marked
*assumption: confirm with team*. The copyright page says what the book is not a substitute
for.
