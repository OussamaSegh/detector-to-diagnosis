# Detector to Diagnosis: MiniDAQ and book sources

Companion repository for *Detector to Diagnosis: Building Regulated Medical Imaging Software in
Modern C++*.

**Download the book:** EPUB and PDF of every release are on the
[download page](https://oussamasegh.github.io/detector-to-diagnosis/).

This repository contains:

| Path | What |
|---|---|
| `minidaq/` | MiniDAQ, a simulated PET data acquisition chain in C++20, grown one milestone per chapter |
| `exercises/chNN/` | Every coding exercise: `starter/` (TODOs, failing tests), `solution/`, shared `tests/` |
| `measurements/chNN/` | The raw results behind every number the book quotes, and the scripts that regenerate them |
| `docs/` | Architecture, decision records and the regulatory file (from Part III) |
| `benchmarks/`, `fuzz/`, `tools/`, `ci/` | Benchmarks, fuzzers, generators and CI scripts |
| `book/` | The book and solutions manual sources (Pandoc Markdown) and their build script |

MiniDAQ is a learning project, not a medical device.

## Quick start (Ubuntu 24.04, about 10 minutes)

The book's front matter, *How to use this book*, has the full step-by-step guide: what to
install, building and testing, a first MiniDAQ session, working from the chapter tags, and doing
the exercises. The short version:

```bash
sudo apt-get install -y build-essential cmake ninja-build git clang-18 libclang-rt-18-dev
git clone <this repo> minidaq && cd minidaq      # or unzip minidaq-vX.Y.Z.zip
ci/run_all.sh                                    # configure, build and test: GCC, Clang, ASan+UBSan
```

`ci/run_all.sh` runs the same gates as CI. To work with one configuration:

```bash
cmake --preset debug            # or: release, clang-release, asan-ubsan, tsan, coverage
cmake --build --preset debug
ctest --preset debug -LE starter
```

MiniDAQ uses Linux interfaces and builds on Linux only, x86-64 or aarch64.
**Mac with Apple silicon:** work in an Ubuntu 24.04 ARM64 virtual machine (OrbStack:
`orb create ubuntu:noble minidaq`, then `orb -m minidaq`; or UTM) and follow the Ubuntu
instructions there; *How to use this book* lists what differs on ARM.
**Windows:** follow the Ubuntu instructions inside WSL2 with an Ubuntu 24.04 distribution.

Offline builds: configure with `-DMINIDAQ_USE_SYSTEM_DEPS=ON` after
`sudo apt-get install libgtest-dev libgmock-dev`.

## Chapters and tags

Every chapter's milestone is a git tag: `git checkout ch05` gives you the repository at the
end of Chapter 5, which is the starting point of Chapter 6. `ch00` is the empty starting
point. Book releases are tagged `book-vX.Y.Z`.

## Tools

After a build, the tools are in `build/<preset>/minidaq/apps/`. Each prints its usage with
`--help`.

| Tool | Chapter | What it does |
|---|---|---|
| `minidaq_server`, `minidaq_ctl` | 6 | The acquisition service behind the TCP control API, and its command-line client |
| `minidaq_jitter`, `minidaq_latency` | 4, 11 | Wake-up jitter; per-stage service time, end-to-end latency and the first bottleneck |
| `minidaq_sim` | 8, 10 to 12 | The detector simulator, the sorter classified by ground truth, dead time, NEMA-style count rates, list-mode output |
| `minidaq_send` | 9 | A simulated readout link: MDQ-R1 packets over UDP, with optional loss and reordering |
| `minidaq_listmode` | 12 | Inspect, verify and histogram MDQ-L1 list-mode files |

The list-mode format is specified in [`docs/formats/mdq-l1.md`](docs/formats/mdq-l1.md).

## Exercises

```bash
cmake --preset debug -B build/mine -DMINIDAQ_BUILD_STARTERS=ON
cmake --build build/mine
ctest --test-dir build/mine -L starter -R ch01/e1     # your work: fails until you solve it
ctest --test-dir build/mine -L solution -R ch01/e1    # reference solution: always green
```

## Building the book

```bash
sudo apt-get install -y pandoc texlive-xetex texlive-latex-extra texlive-fonts-extra \
  fonts-texgyre fonts-inconsolata graphviz librsvg2-bin latexmk epubcheck
book/build.sh            # EPUB + PDF of the book and the solutions manual into book/build/out/
```
