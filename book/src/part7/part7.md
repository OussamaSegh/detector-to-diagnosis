# Part VII: Scientific Python and the build {.part}

Part VII (two chapters) is about the tools around the product. By the end of Part VI, MiniDAQ had a
C++ server, a calibration procedure, a corrections tool, a reconstruction with a C++ projector and a
set of measurements, all built by one CMake project and tested by one CTest run. The Python parts
had grown the way they usually do in a physics group: one script per question, each with its own
reader and its own fits, run with whatever Python the machine had.

That works until a number from one of those scripts decides something. A daily quality check that
says the scanner may be used, an acceptance test that says the detector meets its specification, a
figure in a design review: each of these is evidence, and evidence has to be right, reproducible,
and traceable to the data and code that produced it. The same is true of the build that turns the
source into the product: which compiler, which flags, which versions of which libraries, and whether
someone else can produce the same binary next year.

- **Chapter 31** turns the analysis into an installable Python package: a list-mode reader through a
  memory map for runs larger than memory, maximum likelihood fits for Poisson counts with honest
  errors, a QC report checked against the limits of a protocol file, the provenance of every report,
  and a pinned environment that CI rebuilds.
- **Chapter 32** is CMake and dependency management in full depth: targets and their usage
  requirements, generator expressions, presets, toolchains, installing and exporting a library so
  that another project can use it, how dependencies are pinned and reviewed as SOUP, a Python wheel
  built from C++, and the developer tooling that keeps a codebase consistent.
