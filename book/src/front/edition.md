```{=latex}
\frontmatter
```

# About this edition {.unnumbered}

This is **version {{version}}** ({{date}}) of *The NeuroLF Engineer*, a work-in-progress edition released Part by Part.
Each Part bumps the minor version; the complete, packaged book is version 1.0.0. The
version of this file is printed on the title page and in every output file name.

| Part | Chapters | Version | Status |
|---|---|---|---|
| I. Modern, low-latency C++ | 1 to 7 | 0.1.0 | complete |
| II. PET physics and data acquisition | 8 to 12 | 0.2.0 | complete |
| III. Medical device software standards | 13 to 17 | 0.3.0 | complete |
| IV. Testing, verification and quality | 18 to 21 | 0.4.0 | planned |
| V. Hardware, embedded Linux and networking | 22 to 25 | 0.5.0 | planned |
| VI. Calibration, corrections and reconstruction | 26 to 30 | 0.6.0 | planned |
| VII. Python and tooling | 31 to 32 | 0.7.0 | planned |
| VIII. Capstone and day-one readiness | 33 to 34 | 0.8.0 | planned |

The companion repository (`minidaq-vX.Y.Z.zip`) contains MiniDAQ with one git tag per
chapter written so far (`ch00` is the empty starting point, then `ch01`, `ch02` and so on),
and every exercise starter and solution; the Python analysis package and the complete
regulatory file arrive with the later Parts. Every code listing in this book is included from
that repository at build time, so every listing is compiled and tested.

**This book is for learning.** It is not a substitute for your company's quality management
system, procedures or training, and nothing in it describes any manufacturer's actual
processes or NeuroLF's internal design. Hardware numbers for NeuroLF are typical values
for a brain PET scanner and are marked *assumption: confirm with team*.
